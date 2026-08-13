# iOS e Swift nativo

A `vibe-security` cobre React Native e Expo. Esta referência cobre Swift nativo, que tem
superfície de ataque diferente e ferramentas próprias.

---

## Armazenamento de credencial e dado sensível

**A falha mais comum e mais grave.** `UserDefaults` é um plist em texto claro dentro do
contêiner do app. Qualquer backup não cifrado, qualquer aparelho com jailbreak e qualquer
extração forense lê tudo.

```swift
// ERRADO — texto claro no disco
UserDefaults.standard.set(token, forKey: "authToken")

// CERTO — Keychain, com acessibilidade restrita
let query: [String: Any] = [
    kSecClass as String: kSecClassGenericPassword,
    kSecAttrAccount as String: "authToken",
    kSecValueData as String: Data(token.utf8),
    kSecAttrAccessible as String: kSecAttrAccessibleWhenUnlockedThisDeviceOnly
]
SecItemAdd(query as CFDictionary, nil)
```

**O que auditar:**

- `grep -rn "UserDefaults" --include='*.swift'` e verificar o que está sendo gravado. Token,
  senha, chave, e-mail, CPF e localização não podem estar ali.
- Acessibilidade do Keychain: `kSecAttrAccessibleAlways` é proibido. O padrão sensato é
  `kSecAttrAccessibleWhenUnlockedThisDeviceOnly` — o sufixo `ThisDeviceOnly` impede que o
  item viaje em backup para outro aparelho.
- SwiftData e Core Data: o arquivo do banco herda a proteção de arquivo do app. Para dado
  sensível, exija `.completeFileProtection` ou cifra na camada de aplicação.

## Proteção de arquivo

```swift
try data.write(to: url, options: .completeFileProtection)
```

Sem isso, o arquivo é legível enquanto o aparelho estiver desbloqueado por qualquer processo
com acesso ao contêiner. Auditar toda escrita em disco de conteúdo sensível.

## Exclusão de backup

Dado que não deve sair do aparelho precisa ser marcado, senão vai para o iCloud e para o
backup local:

```swift
var url = fileURL
var values = URLResourceValues()
values.isExcludedFromBackup = true
try url.setResourceValues(values)
```

Auditar especialmente em app que promete "os dados não saem do aparelho" — a promessa quebra
silenciosamente pelo backup.

---

## Segredos no binário

**String em código Swift está em texto claro no binário.** `strings` no `.app` extrai.

```bash
# na auditoria, contra o app compilado
strings MeuApp.app/MeuApp | grep -iE 'sk-|api[_-]?key|secret|bearer|password|AIza'
```

**Regra:** chave de API de serviço pago nunca vai no app. Vai num backend que faz proxy. Se
o app fala direto com OpenAI, Anthropic ou Gemini usando chave embutida, **é Crítico** — a
chave é extraível e a fatura é do dono.

Exceção legítima: chaves públicas por design (identificador do Firebase, chave publicável do
Stripe, chave anônima do Supabase com RLS ativo). Confirme que o RLS existe antes de aceitar
a chave anônima como segura.

---

## App Transport Security

Auditar o `Info.plist`:

```xml
<!-- PROIBIDO em produção -->
<key>NSAppTransportSecurity</key>
<dict><key>NSAllowsArbitraryLoads</key><true/></dict>
```

`NSAllowsArbitraryLoads` desliga a exigência de TLS para todo o app. Se existir, exija
exceção por domínio (`NSExceptionDomains`) e justificativa. A Apple também pede justificativa
na revisão.

---

## Área de transferência

Conteúdo copiado vai para o *pasteboard* geral, é lido por qualquer app e, com Handoff,
atravessa para outros aparelhos.

```swift
// Em app de cofre, senha ou dado sensível:
UIPasteboard.general.setItems(
    [[UIPasteboard.typeAutomatic: senha]],
    options: [.localOnly: true, .expirationDate: Date().addingTimeInterval(60)]
)
```

`.localOnly` impede a travessia entre aparelhos e `.expirationDate` limpa sozinho. Auditar
todo `UIPasteboard.general.string = ` sem opções.

---

## Captura de tela e alternador de apps

O iOS fotografa a tela ao mandar o app para segundo plano, e a imagem fica no disco. Em app
que mostra dado sensível, cobrir na saída:

```swift
func sceneWillResignActive(_ scene: UIScene) {
    // sobrepor uma view opaca antes do snapshot
}
```

Auditar em cofre, app financeiro e app de saúde. Não é obrigatório em app comum.

---

## Deep links e URL schemes

Todo parâmetro de deep link é **entrada não confiável**. Qualquer app instalado pode
disparar seu scheme.

```swift
// ERRADO — confia no parâmetro
func handle(url: URL) {
    let id = url.queryParam("userId")
    carregarPerfil(id)   // acesso a perfil arbitrário
}
```

Auditar: o handler valida sessão antes de agir? Executa ação com efeito colateral (compra,
exclusão, mudança de configuração) sem confirmação? Universal Links são mais seguros que
custom schemes porque exigem o arquivo `apple-app-site-association` no domínio — prefira.

---

## Biometria não é autenticação

`LAContext.evaluatePolicy` retorna um booleano no processo do app, e processo do app é
manipulável em aparelho comprometido. Biometria serve para **desbloquear um segredo guardado
no Keychain**, não para decidir acesso por conta própria.

```swift
// CERTO — a biometria libera o item do Keychain, e o segredo é que autoriza
let access = SecAccessControlCreateWithFlags(
    nil, kSecAttrAccessibleWhenUnlockedThisDeviceOnly,
    .biometryCurrentSet, nil
)
```

`.biometryCurrentSet` invalida o item se o usuário cadastrar uma digital ou face nova — é o
que impede que alguém com o aparelho desbloqueado adicione a própria biometria.

---

## Manifesto de privacidade e APIs de motivo obrigatório

Desde 2024 a Apple exige `PrivacyInfo.xcprivacy` declarando uso de APIs de "motivo
obrigatório" (`UserDefaults`, timestamp de arquivo, espaço em disco, boot time) e a
coleta de dados. Ausência causa rejeição na revisão.

Auditar: o manifesto existe? Declara o que o app realmente coleta? **App que promete zero
telemetria e declara coleta no manifesto tem contradição pública** — e vice-versa.

---

## Verificação rápida

```bash
# armazenamento inseguro
grep -rn "UserDefaults" --include='*.swift' . | grep -viE 'test|preview'

# acessibilidade fraca de Keychain
grep -rn "kSecAttrAccessible" --include='*.swift' .

# ATS desligado
grep -rn "NSAllowsArbitraryLoads" --include='*.plist' .

# pasteboard sem opções
grep -rn "UIPasteboard.general" --include='*.swift' .

# possíveis segredos embutidos
grep -rnE '"(sk-|AIza|xox[baprs]-|ghp_)' --include='*.swift' .

# manifesto de privacidade
find . -name 'PrivacyInfo.xcprivacy'
```
