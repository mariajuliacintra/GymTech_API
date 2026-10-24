"""
Aparência dos e-mails enviados pela API (HTML + versão em texto simples).

Este arquivo só monta o texto/HTML; quem envia é o email_service.py e quem o
chama é o verificacao_service.py. Para mudar cores, textos ou nome do app,
mexa só aqui.

COMO VER O RESULTADO SEM ENVIAR NADA (rode na pasta backend/):
    python -m app.services.email_templates
Isso cria o arquivo email_preview.html; abra-o no navegador.

REGRAS DO HTML DE E-MAIL (por isso o código parece "antigo"):
  - layout com <table> e estilos DENTRO de cada tag (style="..."): os programas
    de e-mail (Gmail, Outlook) ignoram <style> e CSS externo;
  - sem imagens: muitos programas as bloqueiam por padrão, e o código precisa
    aparecer sempre;
  - toda versão HTML vai junto com uma versão em texto, usada por quem não
    abre HTML.
"""
from html import escape
from pathlib import Path

# ---------------------------------------------------------------- personalização
NOME_APP = "GymTech"
COR_DESTAQUE = "#CCFF00"        # fundo do retângulo do código
COR_TEXTO_DESTAQUE = "#125601"  # texto sobre o destaque (verde-limão claro pede texto escuro)
COR_FUNDO_PAGINA = "#F2F4F7"
COR_FUNDO_CARTAO = "#FFFFFF"
COR_TEXTO = "#1F2933"
COR_TEXTO_SUAVE = "#52606D"
FONTE = "Arial, Helvetica, sans-serif"
FONTE_CODIGO = "'Courier New', Courier, monospace"


def montar_email_codigo(
    nome: str, codigo: str, motivo: str, validade_minutos: int
) -> tuple[str, str]:
    """
    Devolve (texto_simples, html) do e-mail com o código de verificação.

    `motivo` completa a frase "Você recebeu este e-mail para ...",
    ex.: "redefinição de senha".
    """
    texto = (
        f"Olá, {nome}!\n\n"
        f"Você recebeu este e-mail para {motivo}. "
        "Digite o código abaixo no app para poder concluir a ação!\n\n"
        f"    {codigo}\n\n"
        f"Este código está disponível por {validade_minutos} minutos e só pode ser usado uma vez!\n"
        "Se não foi você quem pediu, ignore este e-mail e não compartilhe o código com ninguém.\n\n"
        f"Att,\n{NOME_APP}"
    )

    # O nome vem do cadastro (texto digitado por uma pessoa): precisa ser
    # "escapado" para que algo como <b> ou <script> nunca vire HTML de verdade.
    nome_html = escape(nome)
    motivo_html = escape(motivo)
    codigo_html = escape(codigo)
    app_html = escape(NOME_APP)

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light only">
<meta name="supported-color-schemes" content="light only">
<title>{app_html}</title>
</head>
<body style="margin:0;padding:0;background-color:{COR_FUNDO_PAGINA};">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="{COR_FUNDO_PAGINA}" style="background-color:{COR_FUNDO_PAGINA};">
  <tr>
    <td align="center" style="padding:24px 12px;">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" bgcolor="{COR_FUNDO_CARTAO}" style="width:100%;max-width:600px;background-color:{COR_FUNDO_CARTAO};border-radius:8px;">
        <tr>
          <td style="padding:32px 32px 0 32px;font-family:{FONTE};font-size:16px;line-height:24px;color:{COR_TEXTO};">
            <p style="margin:0 0 16px 0;font-size:18px;font-weight:bold;">Olá, {nome_html}!</p>
            <p style="margin:0 0 28px 0;">Você recebeu este e-mail para {motivo_html}. Digite o código abaixo no app para poder concluir a ação!</p>
          </td>
        </tr>
        <tr>
          <td align="center" style="padding:0 32px 28px 32px;">
            <table role="presentation" cellpadding="0" cellspacing="0" border="0" align="center">
              <tr>
                <td align="center" bgcolor="{COR_DESTAQUE}" style="background-color:{COR_DESTAQUE};border-radius:8px;padding:16px 22px 16px 32px;font-family:{FONTE_CODIGO};font-size:36px;line-height:40px;font-weight:bold;letter-spacing:10px;color:{COR_TEXTO_DESTAQUE};">{codigo_html}</td>
              </tr>
            </table>
          </td>
        </tr>
        <tr>
          <td style="padding:0 32px 0 32px;font-family:{FONTE};font-size:14px;line-height:21px;color:{COR_TEXTO_SUAVE};">
            <p style="margin:0 0 12px 0;">Este código está disponível por <strong>{validade_minutos} minutos</strong> e só pode ser usado uma vez!</p>
            <p style="margin:0;">Se não foi você quem pediu, ignore este e-mail e não compartilhe o código com ninguém.</p>
          </td>
        </tr>
        <tr>
          <td style="padding:24px 32px 32px 32px;font-family:{FONTE};font-size:16px;line-height:24px;color:{COR_TEXTO};">
            <p style="margin:0;">Att,<br><strong>{app_html}</strong></p>
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>
</body>
</html>
"""
    return texto, html


if __name__ == "__main__":
    # Pré-visualização: gera email_preview.html para abrir no navegador.
    _, pagina = montar_email_codigo("Maria Júlia", "852165", "redefinição de senha", 10)
    destino = Path("email_preview.html")
    destino.write_text(pagina, encoding="utf-8")
    print(f"Pré-visualização criada em {destino.resolve()}")
