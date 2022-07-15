#Envio de e-mail (gmail) utilizando o protocolo de autenticação OAuth2.0

#Necessário criar uma conta Google Developers -- https://console.cloud.google.com/apis/dashboard
#Ative a API do Gmail e conceda o escopo de envio de e-mail em sua conta do Google Developers
#Sempre que for necessário atualizar o token tem que gerar o código de atualização novamente
#informe o e-mail qual é de autenticação

#importar bibliotecas
import requests
import smtplib
from email import encoders
from email.header import Header
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
import logging
import json
import os, sys
from urllib.parse import quote, unquote
import base64

# make it log.info to the console
log = logging.getLogger()
console = logging.StreamHandler()
log.addHandler(console)
log.setLevel(logging.INFO)

#Substitua as seguintes variáveis ​​usando credenciais de sua conta do Google Developers
REDIRECT_URI = "http://localhost:8080/"
CLIENT_ID = "" # Necessário cadastrar na sua conta do Google Developers
CLIENT_SECRET = "" # Nécessário cadastrar sua conta do Google Developers
OAUTH_SCOPE = "https://www.googleapis.com/auth/gmail.send" #API que efetua o envio de e-mail
AUTHORIZATION_CODE = "" # Cole AUTHORIZATION_CODE após gerar o código de autorização - opção 1
ACCESS_TOKEN = REFRESH_TOKEN = "" # Cole REFRESH_TOKEN após gerar token - opção 2

#funcao que gera o código de autorização
def getAUTHORIZATION_CODE():
    payload = "redirect_uri="+str(REDIRECT_URI)+"&scope="+str(OAUTH_SCOPE)+"&prompt=consent&response_type=code&access_type=offline&client_id="+CLIENT_ID
    return "https://accounts.google.com/o/oauth2/v2/auth?"+payload

def getTokens(AUTHORIZATION_CODE):
    payload = "redirect_uri="+str(REDIRECT_URI)+"&code="+str(AUTHORIZATION_CODE)+"&client_secret="+CLIENT_SECRET+"&grant_type=authorization_code&client_id="+CLIENT_ID
    log.info(quote(payload))
    url = "https://oauth2.googleapis.com/token"
    head = {"Content-Type": "application/x-www-form-urlencoded"}
    log.info("payload - "+str(payload))
    response = requests.post(url, headers=head, data=payload)
    log.info("getTokens response - "+str(response))
    log.info("getTokens response.text - "+str(response.text))
    if response.status_code == 200:
        log.info("getTokens response.json()"+str(response.json()))

        # Save ACCESS_TOKEN to your Database
        global ACCESS_TOKEN, REFRESH_TOKEN
        ACCESS_TOKEN = response.json()["access_token"]
        REFRESH_TOKEN = response.json()["refresh_token"]

def is_token_valid(access_token):
    url = "https://www.googleapis.com/oauth2/v1/tokeninfo?access_token="+access_token

    response = requests.get(url)
    log.info("is_token_valid response - "+str(response))
    log.info("is_token_valid response.text - "+str(response.text))
    log.info("is_token_valid response.json() - "+str(response.json()))

    if "error" in response.json():
        log.info("is_token_valid - invalid")
        return "invalid"
    else:
        log.info("is_token_valid - valid")
        return "valid"

def refresh_access_token():
    payload = "client_secret="+CLIENT_SECRET+"&grant_type=refresh_token&refresh_token="+REFRESH_TOKEN+"&client_id="+CLIENT_ID

    url = "https://oauth2.googleapis.com/token"
    head = {"Content-Type": "application/x-www-form-urlencoded"}
    log.info("payload - "+str(payload))
    response = requests.post(url, headers=head, data=payload)
    log.info("refresh_access_token response - "+str(response))
    log.info("refresh_access_token response.text - "+str(response.text))
    log.info("refresh_access_token response.json() - "+str(response.json()))

    if "access_token" in response.json():
        new_access_token = response.json()["access_token"]
    else:
        log.info("error")
        return "error"

    # ATUALIZAR BANCO DE DADOS COM NOVO TOKEN DE ACESSO

    return new_access_token

# projetando seu e-mail usando HTML
def get_html_content(subject, email_content):
    html_email = """
    <!DOCTYPE html>
    <html lang="pt">
    <head>
        <meta charset="utf-8">
        <title>"""+str(subject)+"""</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta name="description" content="">
        <meta name="author" content="">
        <!-- styles -->
        <link href="https://getbootstrap.com/2.3.2/assets/css/bootstrap.css" rel="stylesheet">
        <style>
        body {
            padding-top: 60px; /* 60px to make the container go all the way to the bottom of the topbar */
        }
        </style>
        <link href="https://getbootstrap.com/2.3.2/assets/css/bootstrap-responsive.css" rel="stylesheet">
    </head>
    <body>
        <div class="container">
        <h1>"""+str(subject)+"""</h1>
        <p>"""+str(email_content)+"""</p>
        </div> <!-- /container -->
    </body>
    </html>
    """
    return html_email

def compose_email(receiver_email, subject, email_content, cc_emails):
    html_email = get_html_content(subject, email_content)
    log.info("html content generated")
    EMAIL_FROM = "" # informe o e-mail para o qual é a conta de envio

    msg_html_content = MIMEText(html_email, "html", "utf-8")
    msg = MIMEMultipart("alternative")
    msg["Subject"] = Header(subject, "utf-8").encode()
    msg["From"] = "Test protocol OAut2.0 <"+EMAIL_FROM+">" # Pode substituir onde EMAIL_FROM deveria estar por algo próprio personalizado se você o vinculou ao seu provedor de e-mail e o confirmou
    msg["To"] = receiver_email
    msg["CC"] = ",".join(cc_emails)
    msg.attach(msg_html_content)

    # Obtenha ACCESS_TOKEN do seu banco de dados
    global ACCESS_TOKEN
    status = is_token_valid(ACCESS_TOKEN)
    log.info("ACCESS_TOKEN status - "+str(status))
    if status == "invalid":
        ACCESS_TOKEN = refresh_access_token()

    Authorization = "Bearer "+ACCESS_TOKEN
    head = {"Content-Type": "application/json", "Authorization": Authorization}
    log.info("compose head - "+str(head))
    body = {"raw": base64.urlsafe_b64encode(msg.as_string().encode("utf-8")).decode("utf-8")}

    return head, body

def sendEmail(receiver_email, cc_emails, subject, email_content):
    payload = compose_email(receiver_email, subject, email_content, cc_emails)

    url = "https://www.googleapis.com/gmail/v1/users/me/messages/send"
    response = requests.post(url, headers=payload[0], data=json.dumps(payload[1]))
    log.info("sendEmail response - "+str(response))
    log.info("sendEmail response.text - "+str(response.text))
    log.info("sendEmail response.json() - "+str(response.json()))
    if "labelIds" in response.json():
        if "SENT" in response.json()["labelIds"]:
            return "success"

    return "error"

choice = int(input("""
Selecionar opção:
1. Gerar código de autorização (O código será exibido no navegador após http://enderecoficticio/?code=)
2. Gerar token (Ao rodar a opção 2 deverá copiar o código refresh_token)
3. Enviar Email
"""))

def sendmail():
    receiver_email = input("""Email to send to: """)
    
    response = sendEmail(receiver_email, [], "Funcao de teste de envio de e-mail (Python)", "Funciona! Esse e-mail foi autenticado pelo protocolo OAuth2." " " "By .......")
    log.info("response - "+str(response))

if choice == 1:
    authcodeurl = getAUTHORIZATION_CODE()
    if sys.platform=="win32":
        os.startfile(authcodeurl)
    elif sys.platform=="darwin":
        subprocess.Popen(["open", authcodeurl])
    else:
        try:
            subprocess.Popen(["xdg-open", authcodeurl])
        except OSError:
            log.info("Please open a browser on: "+authcodeurl)

elif choice == 2:
    getTokens(AUTHORIZATION_CODE)

    log.info("---------------------")
    choice = input("""Deseja enviar um e-mail de teste agora? (Y/N): """)

    if choice.lower() == "y" and "Y":
        sendmail()

elif choice == 3:
    sendmail()