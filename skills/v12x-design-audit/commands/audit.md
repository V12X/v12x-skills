---
description: Auditoria de conformidade ao design system, com aplicação das trocas — pelo Método v12x.
argument-hint: [alvo ou instrução — ex.: "auditar antes de publicar"]
---

Invoque a skill `v12x-design-audit` através da ferramenta **Skill** e conduza o processo **completo** dela, sem improvisar uma análise a partir desta frase. A skill é a fonte do método (fases, coletor determinístico, mapa de cobertura, verificação adversarial, veredito).

Alvo / instrução do usuário: $ARGUMENTS

Se $ARGUMENTS estiver vazio, aplique ao repositório do diretório atual. Comece pela fase de ferramentas determinísticas e **confirme quantos arquivos/itens foram varridos antes de qualquer análise** — se der zero, é a ferramenta errada para a stack, não conformidade perfeita (nenhum furo silencioso).
