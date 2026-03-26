import time
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv

# Carregar variáveis de ambiente se houver um arquivo .env
load_dotenv()


from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions


def get_driver():
    options = webdriver.ChromeOptions() if os.name != "nt" else EdgeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    if os.name == "nt":  # Windows (Seu local)
        edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
        if os.path.exists(edge_path):
            options.binary_location = edge_path
        return webdriver.Edge(service=EdgeService(), options=options)
    else:  # Linux (GCP)
        return webdriver.Chrome(service=webdriver.ChromeService(), options=options)


# Configurações de E-mail (Preencha no .env ou aqui)
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
EMAIL_USER = os.getenv("EMAIL_USER", "seu-email@gmail.com")
EMAIL_PASS = os.getenv("EMAIL_PASS", "sua-senha-de-app")  # Use Senha de App do Google
EMAIL_TO = "tiago.coderia@gmail.com"


def send_email(results):
    """Envia os resultados por e-mail."""
    if not results:
        print("Nenhum resultado encontrado para enviar.")
        return

    msg = MIMEMultipart()
    msg["From"] = EMAIL_USER
    msg["To"] = EMAIL_TO
    msg["Subject"] = "Fila CEI Blumenau - Resultados da Consulta"

    body = "Olá Tiago,\n\nAbaixo os resultados encontrados para o protocolo 7808F33C27:\n\n"
    for item in results:
        body += f"- CEI: {item['cei']} | Posição: {item['posicao']}\n"

    body += "\nAtenciosamente,\nRobô de Consulta."
    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)
        server.quit()
        print(f"E-mail enviado com sucesso para {EMAIL_TO}!")
    except Exception as e:
        print(f"Falha ao enviar e-mail: {e}")


def run_bot():
    url = "https://www.blumenau.sc.gov.br/filacei/extrawwbufferfilatransparencia.aspx"
    protocolo = "7808F33C27"

    # Inicializa o Driver de forma resiliente
    driver = get_driver()

    try:
        print(f"Acessando {url}...")
        driver.get(url)

        # Espera o campo de input estar pronto
        wait = WebDriverWait(driver, 20)
        input_protocolo = wait.until(
            EC.presence_of_element_located((By.ID, "vBUFFERFILAINTENCAOPROTOCOLO"))
        )

        print(f"Inserindo protocolo: {protocolo}")
        input_protocolo.clear()
        input_protocolo.send_keys(protocolo)
        input_protocolo.send_keys(Keys.ENTER)

        # Esperar a tabela atualizar. Como é GeneXus/AJAX, o GridContainerDiv é atualizado.
        # Esperar a tabela atualizar. Como é GeneXus/AJAX, o GridContainerDiv é atualizado.
        print("Aguardando carregamento dos dados da tabela...")

        # Em vez de sleep fixo, espera as linhas aparecerem
        try:
            # Esperamos que ao menos uma linha de dados apareça
            # O seletor abaixo busca linhas que começam com GridContainerRow ou que tenham classes GridEven/Odd
            wait.until(
                EC.presence_of_element_located(
                    (
                        By.CSS_SELECTOR,
                        "#GridContainerDiv tr.GridEven, #GridContainerDiv tr.GridOdd",
                    )
                )
            )
            # Pequena pausa adicional para garantir a renderização total do AJAX
            time.sleep(2)
        except Exception:
            print("Tempo de espera excedido ou nenhuma linha encontrada após busca.")

        print("Extraindo dados da tabela...")
        results = []

        # Seleciona todas as linhas da tabela dentro do Grid (exceto o cabeçalho se houver)
        rows = driver.find_elements(By.CSS_SELECTOR, "#GridContainerDiv table tr")
        print(f"Total de linhas encontradas no container: {len(rows)}")

        for row in rows:
            # Tenta pegar as colunas de cada linha
            cols = row.find_elements(By.TAG_NAME, "td")

            # Se a linha tiver colunas suficientes, é uma linha de dados
            if len(cols) >= 8:
                try:
                    # CEI é índice 2, Posição é índice 7
                    cei = cols[2].text.strip()
                    posicao = cols[7].text.strip()

                    # Ignora linhas de cabeçalho ou vazias que possam ter passado no filtro
                    if cei and posicao and not cei.lower().startswith("cei"):
                        results.append({"cei": cei, "posicao": posicao})
                        print(f"Encontrado: {cei} | Posição: {posicao}")
                except Exception:
                    continue

        if results:
            send_email(results)
        else:
            print(
                "Nenhum dado encontrado na tabela. Verifique se o protocolo está correto ou se a página carregou as informações."
            )

    finally:
        driver.quit()


if __name__ == "__main__":
    run_bot()
