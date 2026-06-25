from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import urllib.parse
from bs4 import BeautifulSoup

app = FastAPI(
    title="Nexus API Gateway",
    description="Microsserviço de orquestração e extração limpa da PGFN via Scrape.do"
)

class ConsultaPGFN(BaseModel):
    cpf_cnpj: str

@app.post("/api/scrape-pgfn")
async def buscar_pgfn(consulta: ConsultaPGFN):
    
    SCRAPE_DO_TOKEN = "e8bcafd2393d4e55867b83b8da4b0106f505095266b" 
    target_url = urllib.parse.quote("https://www.listadevedores.pgfn.gov.br/")
    
    api_url = f"http://api.scrape.do/?url={target_url}&token={SCRAPE_DO_TOKEN}&super=true&render=true"

    interactions = [
        {"action": "wait", "timeout": 4000},
        {"action": "type", "selector": "#identificacaoInput", "text": consulta.cpf_cnpj},
        {"action": "evaluate", "script": "document.querySelector('#identificacaoInput').dispatchEvent(new Event('input', { bubbles: true })); document.querySelector('button.btn-warning').removeAttribute('disabled');"},
        {"action": "click", "selector": "button.btn-warning"},
        {"action": "waitForSelector", "selector": "dev-resultados", "timeout": 20000}
    ]

    headers = {
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(timeout=80.0) as client:
        try:
            response = await client.request(
                "GET",
                api_url, 
                headers=headers, 
                json={"interactions": interactions}
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=f"Erro no Scrape.do: {response.text}")
            
            # --- INÍCIO DA LIMPEZA DE DADOS (BEAUTIFUL SOUP) ---
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Buscamos especificamente a tag de resultados da Receita
            bloco_resultados = soup.find("dev-resultados")
            
            if bloco_resultados:
                # Extrai apenas os textos, separados por ' | ', e remove os espaços inúteis
                texto_limpo = bloco_resultados.get_text(separator=" | ", strip=True)
            else:
                texto_limpo = "Bloco de resultados não encontrado. Possível instabilidade na página do governo."
            
            return {
                "status": "success",
                "cpf_cnpj": consulta.cpf_cnpj,
                "resultado": texto_limpo
            }
            
        except httpx.ReadTimeout:
            raise HTTPException(status_code=504, detail="Timeout: O Scrape.do demorou muito para devolver a tabela.")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erro de comunicação: {str(e)}")
