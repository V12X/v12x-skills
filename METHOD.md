# O Método v12x

*Auditoria de segurança em que dá para confiar o suficiente para agir.*

**Português** · [English](METHOD.en.md)

Na era do código gerado por IA, quase todo mundo audita e quase ninguém confia no resultado.
Auditoria de segurança falha de dois jeitos, e os dois são fatais de formas opostas: ou ela
**gera ruído** — falso positivo que treina o leitor a ignorar o relatório inteiro — ou ela
**gera falsa confiança** — uma nota bonita por cima de um buraco.

O Método v12x são quatro regras que produzem o contrário disso: uma auditoria **reprodutível,
honesta sobre o que não viu, com cada achado verificado, e terminada num veredito** — não numa
métrica. O teste do método é simples: *você consegue decidir publicar com base nela?*

É um método, não uma ferramenta. Qualquer pessoa pode segui-lo com scanners de código aberto e
disciplina de relatório. A [`v12x-scan`](README.md) é a implementação de referência.

---

## Tese 1 — Ferramenta antes de opinião

O que um scanner determinístico acha, ele acha **melhor, mais barato e sem alucinar**. Segredo,
dependência vulnerável, padrão perigoso — isso é trabalho de ferramenta, e a ferramenta ganha
sempre. A leitura crítica — humana ou por IA — é cara e falível, então ela é reservada para
onde a ferramenta **não alcança**: autorização por objeto, isolamento entre inquilinos, lógica
de negócio. Gastar julgamento onde um `grep` resolveria é desperdício; confiar em julgamento
onde só ele resolve é o valor.

> **Contraexemplo.** Pedir a um modelo "procure segredos neste repositório" e confiar na
> resposta. Ele vai perder o `.env` ignorado pelo git — que é justamente onde mora a chave real
> — e ainda inventar um segredo num `example.com`. `gitleaks` no histórico não faz nenhuma das
> duas coisas.

## Tese 2 — Nenhum furo silencioso

*"Não achei nada"* e *"não olhei"* são frases diferentes, e um relatório ruim funde as duas. O
método exige um **mapa de cobertura**: toda auditoria declara o que ficou de fora — ferramenta
ausente, diretório pulado, categoria que não se aplica, linguagem não coberta. Um furo
declarado é administrável: o leitor sabe onde ainda precisa olhar. Um furo silencioso é o que
derruba, porque ele se disfarça de cobertura.

> **Contraexemplo.** Um relatório que afirma *"nenhuma vulnerabilidade de dependência"* quando o
> scanner de dependência nem estava instalado. A frase é tecnicamente verdadeira e
> completamente enganosa — passa uma confiança que não foi conquistada.

## Tese 3 — Refute antes de reportar

Auditoria por leitura tem taxa alta de falso positivo, e **um único falso positivo destrói a
confiança no relatório inteiro** — o leitor aprende a descartar tudo. Por isso nenhum achado
entra no relatório sem sobreviver a uma tentativa **explícita de refutação**: existe validação
numa camada anterior? um middleware que já barra? uma política de banco que já cobre? Se o
achado morre nessa prova, ótimo — ele não devia estar lá. Cinco achados que sobrevivem valem
mais que trinta candidatos dos quais vinte são ruído.

> **Contraexemplo.** Reportar um `dangerouslySetInnerHTML` como XSS sem checar que o conteúdo é
> uma constante escrita no próprio código. Um falso positivo assim, e o desenvolvedor descarta
> os outros vinte e nove achados — inclusive o que era real.

## Tese 4 — Veredito, não pontuação

Nunca resuma a segurança de uma base num número de 0 a 100, nem num "Passou/Falhou" por
categoria. A nota **não é reprodutível** (a mesma base auditada duas vezes dá notas
diferentes), **dá falsa confiança** ("87, dá para publicar") e **esconde severidade** (dezenove
checagens boas e uma credencial exposta ainda pontuam alto — que é exatamente o caso perigoso).
A indústria pontua **cada vulnerabilidade** com rubrica definida — é o que o CVSS faz — nunca
uma base inteira de forma holística. O substituto correto é **contagem por severidade + um
veredito binário de publicação**.

> **Contraexemplo.** *"Segurança: 92/100 ✅"* num repositório que traz a chave `service_role` do
> Supabase embutida no bundle do cliente. Uma credencial basta para o comprometimento total;
> nenhuma média aritmética expressa isso. O veredito correto é uma palavra: **não publicar**.

---

## Auditoria é ciclo, não evento

Uma auditoria pontual não deixa nada "à prova de furo" — o código muda no dia seguinte. O que
aproxima disso é fechar o ciclo:

1. **Persistir o relatório** e **diffar contra o anterior.** O achado que voltou é regressão, e
   regressão sobe um nível de severidade.
2. **Cada correção vira verificação permanente.** "Token em log" corrigido nasce como um teste
   no CI que falha se o padrão voltar. Achado que só vive no relatório volta.
3. **Reauditar depois de corrigir.** Correção de segurança introduz regressão com frequência
   irritante.

Se nada disso roda sozinho, tudo depende de alguém lembrar — e essa dependência **é um achado
por si**.

---

## Implementação de referência

A [`v12x-scan`](README.md) aplica o método como uma skill do [Claude
Code](https://claude.com/claude-code): fase determinística primeiro, análise por camada,
verificação adversarial, severidade por consequência e relatório com mapa de cobertura e
veredito. Mas o método não depende dela. Para adotá-lo sem a ferramenta, o mínimo é:

- scanners determinísticos primeiro (segredos no histórico **e** na árvore, dependências,
  padrões estáticos), com cada ausência registrada como não coberta;
- leitura reservada para autorização e isolamento;
- refutação explícita de cada achado antes de reportar;
- relatório que termina em contagem por severidade + veredito, nunca em nota.

## Como citar

> Método v12x — auditoria de segurança em quatro teses. https://github.com/V12X/v12x-skills

Documento vivo, sob licença [MIT](LICENSE). Discordâncias fundamentadas melhoram o método —
abra uma issue.
