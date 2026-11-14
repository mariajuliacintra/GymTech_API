"""
Aparência dos e-mails enviados pela API (HTML + versão em texto simples).

Este arquivo só monta o texto/HTML; quem envia é o email_service.py e quem o
chama são os services (verificacao_service.py e notificacao_service.py).
Para mudar cores, textos ou nome do app, mexa só aqui.

COMO VER O RESULTADO SEM ENVIAR NADA (rode na pasta backend/):
    python -m app.services.email_templates
Isso cria o arquivo email_preview.html; abra-o no navegador.

REGRAS DO HTML DE E-MAIL (por isso o código parece "antigo"):
  - layout com <table> e estilos DENTRO de cada tag (style="..."): os programas
    de e-mail (Gmail, Outlook) ignoram <style> e CSS externo;
  - sem imagens: muitos programas as bloqueiam por padrão, e o conteúdo precisa
    aparecer sempre;
  - toda versão HTML vai junto com uma versão em texto, usada por quem não
    abre HTML.
"""
from datetime import date
from html import escape
from pathlib import Path

# ---------------------------------------------------------------- personalização
NOME_APP = "GymTech"
COR_DESTAQUE = "#CCFF00"        # fundo do retângulo de destaque
COR_TEXTO_DESTAQUE = "#125601"  # texto sobre o destaque (verde-limão claro pede texto escuro)
COR_FUNDO_PAGINA = "#F2F4F7"
COR_FUNDO_CARTAO = "#FFFFFF"
COR_TEXTO = "#1F2933"
COR_TEXTO_SUAVE = "#52606D"
COR_BORDA = "#E4E7EB"
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


def montar_email_lembrete_treino(
    nome_aluno: str,
    titulo_treino: str,
    data_programada: date,
    dias_restantes: int,
    nome_profissional: str,
    nome_academia: str,
    exercicios: list[dict],
) -> tuple[str, str]:
    """
    Devolve (texto_simples, html) do lembrete de treino próximo para o aluno.
    """
    data_fmt = data_programada.strftime("%d/%m/%Y")
    if dias_restantes <= 0:
        quando_texto = f"hoje ({data_fmt})"
        selo_texto = f"HOJE • {data_fmt}"
    elif dias_restantes == 1:
        quando_texto = f"amanhã ({data_fmt})"
        selo_texto = f"AMANHÃ • {data_fmt}"
    else:
        quando_texto = f"em {dias_restantes} dias ({data_fmt})"
        selo_texto = f"EM {dias_restantes} DIAS • {data_fmt}"

    linhas_texto = []
    linhas_html = []
    for idx, ex in enumerate(exercicios, start=1):
        nome_ex = ex["nome_exercicio"]
        grupo = ex["grupo_muscular"]
        series = ex["series"]
        reps = ex["repeticoes"]
        carga = ex.get("carga_sugerida")
        descanso = ex.get("tempo_descanso")

        detalhes = [f"{series}x{reps}"]
        if carga is not None:
            detalhes.append(f"{carga:g} kg")
        if descanso is not None:
            detalhes.append(f"descanso {descanso}")
        resumo_detalhes = " | ".join(detalhes)

        linhas_texto.append(f"  {idx}. {nome_ex} ({grupo}) — {resumo_detalhes}")
        linhas_html.append(
            f"""<tr>
              <td style="padding:10px 12px;border-bottom:1px solid {COR_BORDA};font-family:{FONTE};font-size:14px;line-height:20px;color:{COR_TEXTO};">
                <strong>{idx}. {escape(nome_ex)}</strong><br>
                <span style="font-size:12px;color:{COR_TEXTO_SUAVE};">{escape(grupo)}</span>
              </td>
              <td align="right" style="padding:10px 12px;border-bottom:1px solid {COR_BORDA};font-family:{FONTE};font-size:13px;line-height:20px;color:{COR_TEXTO};white-space:nowrap;">
                {escape(resumo_detalhes)}
              </td>
            </tr>"""
        )

    bloco_exercicios_texto = (
        "Exercícios programados:\n" + "\n".join(linhas_texto) + "\n\n"
        if linhas_texto
        else ""
    )

    texto = (
        f"Olá, {nome_aluno}!\n\n"
        f'Lembrete da {nome_academia}: o seu treino "{titulo_treino}" está programado para {quando_texto}.\n'
        f"Profissional responsável: {nome_profissional}\n\n"
        f"{bloco_exercicios_texto}"
        "Prepare sua garrafa de água, chegue no horário e bom treino!\n\n"
        f"Att,\n{NOME_APP} - {nome_academia}"
    )

    nome_aluno_html = escape(nome_aluno)
    titulo_html = escape(titulo_treino)
    prof_html = escape(nome_profissional)
    acad_html = escape(nome_academia)
    selo_html = escape(selo_texto)
    app_html = escape(NOME_APP)

    tabela_exercicios_html = ""
    if linhas_html:
        tabela_exercicios_html = f"""
        <tr>
          <td style="padding:0 32px 24px 32px;">
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border:1px solid {COR_BORDA};border-radius:6px;border-collapse:collapse;">
              <tr>
                <td colspan="2" bgcolor="#F8FAFC" style="background-color:#F8FAFC;padding:10px 12px;border-bottom:1px solid {COR_BORDA};font-family:{FONTE};font-size:12px;font-weight:bold;text-transform:uppercase;letter-spacing:0.5px;color:{COR_TEXTO_SUAVE};">
                  Ficha do treino ({len(linhas_html)} exercício{"s" if len(linhas_html) != 1 else ""})
                </td>
              </tr>
              {"".join(linhas_html)}
            </table>
          </td>
        </tr>"""

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
            <p style="margin:0 0 12px 0;font-size:18px;font-weight:bold;">Olá, {nome_aluno_html}!</p>
            <p style="margin:0 0 24px 0;">O seu próximo treino na <strong>{acad_html}</strong> está chegando:</p>
          </td>
        </tr>
        <tr>
          <td style="padding:0 32px 24px 32px;">
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="{COR_DESTAQUE}" style="background-color:{COR_DESTAQUE};border-radius:8px;">
              <tr>
                <td style="padding:20px 24px;font-family:{FONTE};color:{COR_TEXTO_DESTAQUE};">
                  <div style="font-size:12px;font-weight:bold;letter-spacing:1px;text-transform:uppercase;margin-bottom:6px;">{selo_html}</div>
                  <div style="font-size:22px;line-height:28px;font-weight:bold;margin-bottom:6px;">{titulo_html}</div>
                  <div style="font-size:14px;line-height:20px;">Profissional: <strong>{prof_html}</strong></div>
                </td>
              </tr>
            </table>
          </td>
        </tr>
        {tabela_exercicios_html}
        <tr>
          <td style="padding:0 32px 0 32px;font-family:{FONTE};font-size:14px;line-height:21px;color:{COR_TEXTO_SUAVE};">
            <p style="margin:0;">Prepare sua garrafa de água, chegue no horário e bom treino!</p>
          </td>
        </tr>
        <tr>
          <td style="padding:24px 32px 32px 32px;font-family:{FONTE};font-size:16px;line-height:24px;color:{COR_TEXTO};">
            <p style="margin:0;">Att,<br><strong>{app_html} • {acad_html}</strong></p>
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
    _, pagina = montar_email_lembrete_treino(
        "Maria Júlia",
        "Treino A - Superiores",
        date.today(),
        1,
        "Carlos Treinador",
        "GymTech Franca",
        [
            {
                "nome_exercicio": "Supino reto",
                "grupo_muscular": "Peito",
                "series": 4,
                "repeticoes": 12,
                "carga_sugerida": 30.0,
                "tempo_descanso": "00:01:30",
            }
        ],
    )
    destino = Path("email_preview.html")
    destino.write_text(pagina, encoding="utf-8")
    print(f"Pré-visualização criada em {destino.resolve()}")
