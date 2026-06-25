from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from bs4 import BeautifulSoup

app = FastAPI(
    title="Nexus API Crawler",
    description="Orquestração robusta PGFN: Proxy Residencial + Extração Limpa"
)

class ConsultaPGFN(BaseModel):
    cpf_cnpj: str

@app.post("/api/scrape-pgfn")
async def buscar_pgfn(consulta: ConsultaPGFN):
    
    SCRAPE_DO_TOKEN = "e8bcafd2393d4e55867b83b8da4b0106f505095266b" 
    
    # O Scrape.do agora atua como escudo de rede (Proxy Residencial)
    browser_config = BrowserConfig(
        headless=True,
        browser_type="chromium",
        proxy=f"http://{SCRAPE_DO_TOKEN}:@proxy.scrape.do:8080"
    )

    # O nosso hack implacável contra o Angular
    js_bruto = f"""
    (async () => {{
        await new Promise(r => setTimeout(r, 4000));
        let input = document.querySelector('#identificacaoInput');
        if(input) {{
            input.value = '{consulta.cpf_cnpj}';
            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
            input.dispatchEvent(new Event('change', {{ bubbles: true }}));
            input.dispatchEvent(new Event('blur', {{ bubbles: true }}));
            
            await new Promise(r => setTimeout(r, 1000));
            
            let btn = document.querySelector('button.btn-warning');
            if(btn) {{
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

            if not result.success:
                raise HTTPException(status_code=500, detail=result.error_message)

            # Limpeza cirúrgica com BeautifulSoup
            soup = BeautifulSoup(result.html, "html.parser")
            bloco_resultados = soup.find("dev-resultados")
            
            if bloco_resultados:
                texto_limpo = bloco_resultados.get_text(separator=" | ", strip=True)
            else:
                texto_limpo = "Erro: A tabela não apareceu após o clique."

            return {
                "status": "success",
                "cpf_cnpj": consulta.cpf_cnpj,
                "resultado": texto_limpo
            }
                
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erro interno do crawler: {str(e)}")
