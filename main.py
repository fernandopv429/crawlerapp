from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import urllib.parse

app = FastAPI(
    title="Nexus API Gateway",
    description="Microsserviço ultraleve de orquestração para PGFN via Scrape.do"
)

class ConsultaPGFN(BaseModel):
    cpf_cnpj: str

@app.post("/api/scrape-pgfn")
async def buscar_pgfn(consulta: ConsultaPGFN):
    
    SCRAPE_DO_TOKEN = "e8bcafd2393d4e55867b83b8da4b0106f505095266b" 
    target_url = urllib.parse.quote("https://www.listadevedores.pgfn.gov.br/")
    
    # URL da API instruindo o Scrape.do a abrir o navegador (render=true) usando IPs residenciais (super=true)
    api_url = f"http://api.scrape.do/?url={target_url}&token={SCRAPE_DO_TOKEN}&super=true&render=true"

    # A Mágica da Documentação: Enviamos o roteiro exato para os robôs do Scrape.do executarem
    interactions = [
        {"action": "wait", "timeout": 4000},
        {"action": "type", "selector": "#identificacaoInput", "text": consulta.cpf_cnpj},
        # Forçamos o Angular a acordar e destravamos o botão
        {"action": "evaluate", "script": "document.querySelector('#identificacaoInput').dispatchEvent(new Event('input', { bubbles: true })); document.querySelector('button.btn-warning').removeAttribute('disabled');"},
        # Clicamos
        {"action": "click", "selector": "button.btn-warning"},
        # Esperamos a tabela aparecer antes deles nos devolverem o HTML
        {"action": "waitForSelector", "selector": "dev-resultados", "timeout": 20000}
    ]

    headers = {
        "Content-Type": "application/json"
    }

    # Disparamos a requisição com um limite de 60 segundos (já que o Scrape.do pode demorar um pouco para passar no WAF)
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                api_url, 
                headers=headers, 
                json={"interactions": interactions}
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=f"Erro no Scrape.do: {response.text}")
                
            # O Scrape.do retorna o HTML da página já processada e resolvida
            return {
                "status": "success",
                "cpf_cnpj": consulta.cpf_cnpj,
                # Retornamos os primeiros 5000 caracteres do HTML só para confirmar a extração
                "html_processado": response.text[:5000] 
            }
            
        except httpx.ReadTimeout:
            raise HTTPException(status_code=504, detail="Timeout: O Scrape.do demorou muito para devolver a tabela.")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erro de comunicação: {str(e)}")
