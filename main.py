from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

app = FastAPI(
    title="Nexus Crawler API",
    description="Microsserviço de bypass e extração de dados da PGFN"
)

class ConsultaPGFN(BaseModel):
    cpf_cnpj: str

@app.post("/api/scrape-pgfn")
async def buscar_pgfn(consulta: ConsultaPGFN):
    browser_config = BrowserConfig(
        headless=True,
        browser_type="chromium"
    )

    # Código atualizado para a sintaxe da versão 0.9.0 do Crawl4AI
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        magic=True, 
        
        js_code=[
            f"document.querySelector('#input-cpf-cnpj').value = '{consulta.cpf_cnpj}';",
            "document.querySelector('#btn-consultar').click();"
        ],
        wait_for="css:.tabela-resultados",
        
        # AQUI FOI A MUDANÇA: Parâmetro direto e simplificado
        css_selector=".tabela-resultados" 
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
