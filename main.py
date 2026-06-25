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

    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        magic=True, 
        
        # Injeção Avançada para Angular: Preenche, avisa o framework e clica
        js_code=[
            f"let input = document.querySelector('#identificacaoInput');",
            f"input.value = '{consulta.cpf_cnpj}';",
            "input.dispatchEvent(new Event('input', { bubbles: true }));",
            "document.querySelector('button.btn-warning').click();"
        ],
        
        # Espera o componente de resultados do Angular renderizar na tela
        wait_for="css:dev-resultados",
        
        # Extrai tudo que estiver dentro da tag de resultados (tabela ou aviso de vazio)
        css_selector="dev-resultados" 
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
