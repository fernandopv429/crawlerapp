from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
import base64
import os

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

    # Função assíncrona em JS para simular o comportamento humano pausado
    js_humano = f"""
    (async () => {{
        // Espera 3 segundos pro Angular carregar totalmente
        await new Promise(r => setTimeout(r, 3000));
        
        let input = document.querySelector('#identificacaoInput');
        if(input) {{
            input.value = '{consulta.cpf_cnpj}';
            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
            
            // Espera 1 segundo após digitar
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
        screenshot=True # Ativa a "visão de raio-x" do robô
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        try:
            result = await crawler.arun(
                url="https://www.listadevedores.pgfn.gov.br/",
                config=run_config
            )

            # Se falhar, tentamos salvar o screenshot no disco do servidor para você ver
            if not result.success:
                if result.screenshot:
                    with open("erro_pgfn.jpg", "wb") as f:
                        f.write(base64.b64decode(result.screenshot))
                    print("Screenshot do erro salvo como erro_pgfn.jpg no servidor!")
                    
                raise HTTPException(status_code=500, detail=result.error_message)

            return {
                "status": "success",
                "cpf_cnpj": consulta.cpf_cnpj,
                "dados_extraidos": result.markdown
            }
                
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erro no crawler: {str(e)}")
