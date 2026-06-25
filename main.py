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
    
    SCRAPE_DO_TOKEN = "e8bcafd2393d4e55867b83b8da4b0106f505095266b" 
    
    browser_config = BrowserConfig(
        headless=True,
        browser_type="chromium",
        proxy=f"http://{SCRAPE_DO_TOKEN}:@proxy.scrape.do:8080"
    )

    # Nova injeção de JS: Quebrando a trava do botão
    js_bruto = f"""
    (async () => {{
        await new Promise(r => setTimeout(r, 4000));
        let input = document.querySelector('#identificacaoInput');
        if(input) {{
            input.value = '{consulta.cpf_cnpj}';
            
            // Dispara múltiplos alertas para o Angular acordar
            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
            input.dispatchEvent(new Event('change', {{ bubbles: true }}));
            input.dispatchEvent(new Event('blur', {{ bubbles: true }}));
            
            await new Promise(r => setTimeout(r, 1000));
            
            let btn = document.querySelector('button.btn-warning');
            if(btn) {{
                // O HACK DE OURO: Remove a trava de clique
                btn.removeAttribute('disabled'); 
                btn.click();
            }}
        }}
    }})();
    """

    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        magic=True,
        js_code=js_bruto,
        wait_for="css:dev-resultados",
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
