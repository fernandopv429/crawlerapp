from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from bs4 import BeautifulSoup

app = FastAPI(
    title="Nexus API Crawler",
    description="Orquestração robusta PGFN: Proxy Residencial + Diagnóstico Visual"
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

    # Hack reforçado com foco e desfoque para forçar a validação do Angular
    js_bruto = f"""
    (async () => {{
        await new Promise(r => setTimeout(r, 4000));
        let input = document.querySelector('#identificacaoInput');
        if(input) {{
            input.focus();
            input.value = '{consulta.cpf_cnpj}';
            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
            input.dispatchEvent(new Event('change', {{ bubbles: true }}));
            input.blur();
            
            await new Promise(r => setTimeout(r, 1500));
            
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
        screenshot=True # Ligamos a câmera de segurança
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        try:
            result = await crawler.arun(
                url="https://www.listadevedores.pgfn.gov.br/",
                config=run_config
            )

            # Se der o Timeout, devolvemos a foto da tela para o seu terminal
            if not result.success:
                return {
                    "status": "erro_visual",
                    "detalhe": result.error_message,
                    "imagem_base64": result.screenshot
                }

            soup = BeautifulSoup(result.html, "html.parser")
            bloco_resultados = soup.find("dev-resultados")
            
            # Se o site carregou mas a tabela veio vazia, também capturamos a foto
            if not bloco_resultados:
                return {
                    "status": "erro_visual",
                    "detalhe": "Tabela não encontrada após o clique no botão.",
                    "imagem_base64": result.screenshot
                }
                
            texto_limpo = bloco_resultados.get_text(separator=" | ", strip=True)

            return {
                "status": "success",
                "cpf_cnpj": consulta.cpf_cnpj,
                "resultado": texto_limpo
            }
                
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erro interno do crawler: {str(e)}")
