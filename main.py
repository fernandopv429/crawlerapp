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
            # A CORREÇÃO DE OURO: Forçando o envio do JSON (Interactions) usando o método GET
            response = await client.request(
                "GET",
                api_url, 
                headers=headers, 
                json={"interactions": interactions}
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=f"Erro no Scrape.do: {response.text}")
                
            return {
                "status": "success",
                "cpf_cnpj": consulta.cpf_cnpj,
                "html_processado": response.text[:5000] 
            }
            
        except httpx.ReadTimeout:
            raise HTTPException(status_code=504, detail="Timeout: O Scrape.do demorou muito para devolver a tabela.")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erro de comunicação: {str(e)}")
