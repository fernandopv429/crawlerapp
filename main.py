from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

app = FastAPI(
    title="Nexus Crawler API",
    description="Microsserviço de bypass e extração de dados da PGFN"
)

# Modelo de dados que o n8n vai enviar no corpo da requisição
class ConsultaPGFN(BaseModel):
    cpf_cnpj: str

@app.post("/api/scrape-pgfn")
async def buscar_pgfn(consulta: ConsultaPGFN):
    # Configuração do navegador para rodar dentro do Docker (Headless = True)
    browser_config = BrowserConfig(
        headless=True,
        browser_type="chromium"
    )

    # Configuração de execução com a camuflagem (magic=True) para passar pelo WAF
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        magic=True, 
        page_timeout=30000,
        
        # Injeção de JavaScript para preencher e clicar na página principal da PGFN
        js_code=[
            f"document.querySelector('#input-cpf-cnpj').value = '{consulta.cpf_cnpj}';",
            "document.querySelector('#btn-consultar').click();"
        ],
        wait_for="css:.tabela-resultados",
        extraction_strategy={
            "type": "css",
            "selector": ".tabela-resultados"
        }
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        try:
            result = await crawler.arun(
                url="https://www.listadevedores.pgfn.gov.br/",
                config=run_config
            )

            if result.success:
                return {
                    "status": "success",
                    "cpf_cnpj": consulta.cpf_cnpj,
                    "dados_extraidos": result.markdown
                }
            else:
                raise HTTPException(status_code=500, detail=result.error_message)
                
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erro no crawler: {str(e)}")
