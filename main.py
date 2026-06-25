from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
import base64

app = FastAPI(
    title="Nexus Crawler API",
    description="Microsserviço de bypass e extração de dados da PGFN"
)

class ConsultaPGFN(BaseModel):
    cpf_cnpj: str

@app.post("/api/scrape-pgfn")
async def buscar_pgfn(consulta: ConsultaPGFN):
    
    # O seu Token do Scrape.do (já configurado)
    SCRAPE_DO_TOKEN = "e8bcafd2393d4e55867b83b8da4b0106f505095266b" 
    
    # Configurando o Scrape.do como Super Proxy Residencial
    browser_config = BrowserConfig(
        headless=True,
        browser_type="chromium",
        proxy=f"http://{SCRAPE_DO_TOKEN}:@proxy.scrape.do:8080"
    )

    js_humano = f"""
    (async () => {{
        await new Promise(r => setTimeout(r, 3000));
        let input = document.querySelector('#identificacaoInput');
        if(input) {{
            input.value = '{consulta.cpf_cnpj}';
            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
            await new Promise(r => setTimeout(r, 1000));
            let btn = document.querySelector('button.btn-warning');
            if(btn) btn.click();
        }}
    }})();
    """

    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        magic=True,
        js_code=js_humano,
        wait_for="css:dev-resultados",
        css_selector="dev-resultados",
        screenshot=True 
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        try:
            result = await crawler.arun(
                url="https://www.listadevedores.pgfn.gov.br/",
                config=run_config
            )

            if not result.success:
                if result.screenshot:
                    with open("erro_pgfn.jpg", "wb") as f:
                        f.write(base64.b64decode(result.screenshot))
                raise HTTPException(status_code=500, detail=result.error_message)

            return {
                "status": "success",
                "cpf_cnpj": consulta.cpf_cnpj,
                "dados_extraidos": result.markdown
            }
                
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erro no crawler: {str(e)}")
