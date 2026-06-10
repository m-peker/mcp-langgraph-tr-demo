# Türkçe MCP + LangGraph Öğretici Demo

Bu repo, **Model Context Protocol (MCP)** ile araç sunmayı ve **LangGraph** ile bu araçları kullanan bir ajan akışı kurmayı öğretmek için hazırlanmış kapsamlı ama sade bir demo projedir.

Amaç yalnızca çalışan bir örnek vermek değil; MCP server, MCP client, tool discovery, tool call ve LangGraph agent orchestration kavramlarını birbirinden ayırarak anlatmaktır.

## Kısa Özet

Bu projede:

- `mcp_server.py` MCP server olarak araçları yayınlar.
- `mcp_client.py` server ile STDIO üzerinden JSON-RPC konuşur.
- Client önce MCP handshake yapar.
- Sonra `tools/list` ile araçları keşfeder.
- LangGraph ajanı, kullanıcı isteğine göre uygun tool'u seçer.
- Tool sonucu tekrar LLM'e verilerek Türkçe cevap üretilir.

## MCP ve LangGraph Farkı

**MCP**, LLM uygulamalarına dış araç ve bağlam sağlamanın standart yoludur. Bir tool nasıl tanımlanır, şeması nasıl paylaşılır, client tool'u nasıl çağırır gibi konular MCP'nin alanıdır.

**LangGraph**, ajan akışını yönetir. Hangi adımlar var, hangi düğümden sonra hangi düğüm çalışır, state nasıl taşınır gibi konular LangGraph'ın alanıdır.

Kısa formül:

```text
MCP       = Tool protokolü ve entegrasyon standardı
LangGraph = Ajan akışı ve karar orkestrasyonu
```

Daha detaylı açıklama için: [docs/mcp-vs-langgraph.md](docs/mcp-vs-langgraph.md)

## Mimari

```text
Kullanıcı
  |
  v
LangGraph Agent
  |  route node: tool seçer
  |  respond node: sonucu Türkçe açıklar
  v
MCP Client
  |  initialize
  |  tools/list
  |  tools/call
  v
MCP Server
  |  get_weather
  |  web_search
  |  calculate
  |  convert_units
  |  analyze_text
  |  create_learning_roadmap
  v
Dış API'ler ve lokal deterministik fonksiyonlar
```

## Tool Listesi

| Tool | Amaç | API gerekir mi? |
| --- | --- | --- |
| `get_weather` | Şehir için hava durumu getirir | Hayır, wttr.in kullanır |
| `web_search` | Web araması yapar | Evet, `SERPER_API_KEY` |
| `calculate` | Güvenli aritmetik hesaplar | Hayır |
| `convert_units` | Birim dönüşümü yapar | Hayır |
| `analyze_text` | Metin sayımı ve anahtar kelime çıkarımı yapar | Hayır |
| `create_learning_roadmap` | Öğrenme planı üretir | Hayır |

Bu dağılım özellikle öğretici olsun diye seçildi: bazı tool'lar dış API kullanır, bazıları tamamen deterministiktir. Böylece MCP'nin yalnızca API çağırmak değil, herhangi bir kabiliyeti standart şekilde sunmak olduğu daha net görülür.

## Kurulum

Windows PowerShell için önerilen sıralama:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

PowerShell script çalıştırmayı engellerse yalnızca bu terminal oturumu için:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
.\.venv\Scripts\Activate.ps1
```

Ollama tarafı:

```powershell
ollama pull llama3:latest
ollama serve
```

`ollama serve` zaten çalışan bir Ollama servisi varsa hata verebilir; bu normaldir. Kontrol etmek için:

```powershell
ollama list
```

`.env` dosyasını oluşturun:

```powershell
Copy-Item .env.example .env
```

`.env` içeriği:

```env
OLLAMA_MODEL=llama3:latest
OLLAMA_BASE_URL=http://localhost:11434
SERPER_API_KEY=your_serper_api_key
```

`SERPER_API_KEY` yalnızca `web_search` için gerekir. Diğer lokal tool'lar ve hava durumu örneği onsuz çalışabilir. Bu proje varsayılan olarak OpenAI kullanmaz; LLM çağrıları lokal Ollama API'sine gider.

## Çalıştırma

```bash
python mcp_client.py
```

Client şu sırayla ilerler:

1. `mcp_server.py` dosyasını subprocess olarak başlatır.
2. `initialize` isteği ile MCP handshake yapar.
3. `initialized` notification gönderir.
4. `tools/list` ile server'daki tool'ları keşfeder.
5. LangGraph ajanını Ollama `llama3:latest` ile kurar.
6. Örnek kullanıcı sorularını graph üzerinden çalıştırır.
7. Sonra terminalde `SEN:` prompt'u açılır; buradan kendi sorularınızı yazabilirsiniz.

Çıkmak için:

```text
exit
quit
q
```

## Testler

Testler dış API, OpenAI veya Ollama çağırmaz. Saf tool fonksiyonlarını ve client helper davranışlarını doğrular.

```bash
python -m unittest discover -s tests -v
```

## Lokal LLM Notları

Bu demo varsayılan olarak Ollama üzerinde `llama3:latest` kullanır. Lokal LLM ile çalışmak öğretici ve maliyetsizdir, fakat tool routing konusunda her zaman kusursuz değildir.

Bu yüzden projede iki katmanlı yaklaşım kullanılır:

- Net Türkçe kalıplar deterministik olarak yakalanır: `Bursa hava durumu`, `8+5 kaç yapar`, `(10+71) karekökü nedir`.
- Daha açık uçlu isteklerde LangGraph içindeki LLM router devreye girer.

Özellikle matematik gibi kesinlik isteyen cevaplarda sonuç LLM'e tekrar hesaplatılmaz. `calculate` tool sonucu doğrudan formatlanır. Hava durumu çıktıları da kısa Türkçe şablonla gösterilir; böylece lokal modelin İngilizce API sonucunu garip çevirmesi azaltılır.

Bu bilinçli bir tasarım kararıdır:

```text
LLM karar vermeye yardımcı olur.
Kesin işler tool tarafından yapılır.
Kritik ve sık kullanılan kalıplar kuralla desteklenir.
```

## Dosya Yapısı

```text
.
├── mcp_server.py                 # FastMCP server
├── mcp_client.py                 # MCP client + LangGraph agent
├── tools.py                      # Test edilebilir tool çekirdeği
├── tests/
│   ├── test_tools.py             # Tool davranış testleri
│   └── test_client_helpers.py    # Client helper testleri
├── docs/
│   ├── mcp-vs-langgraph.md       # Kavramsal ayrım
│   └── medium-taslak.md          # Türkçe Medium yazısı taslağı
├── requirements.txt
└── .env.example
```

## Öğrenme Akışı

Bu repoyu incelerken önerilen sıra:

1. `tools.py`: Tool'lar aslında normal Python fonksiyonlarıdır.
2. `mcp_server.py`: Bu fonksiyonlar MCP server üzerinden yayınlanır.
3. `mcp_client.py`: Client handshake, discovery ve call yapar.
4. `build_graph`: LangGraph, MCP tool'larını kullanan ajan akışını kurar.
5. `tests/`: Tool davranışlarının dış servislerden bağımsız test edilebildiğini gösterir.

## Örnek Sorular

```text
Istanbul hava durumu nasıl?
25 * 4 + 10 / 2 kaç eder?
10 kilometre kaç mile eder?
Bu metni analiz et: MCP MCP LangGraph agent agent tool.
MCP ve LangGraph öğrenmek için 7 günlük plan hazırla.
```

## Medium Makalesi

Medium yazısı için ilk taslak: [docs/medium-taslak.md](docs/medium-taslak.md)

Makalenin ana iddiası:

> MCP aracı standartlaştırır; LangGraph ajanın bu aracı ne zaman ve nasıl kullanacağını organize eder.

## Güvenlik Notları

- `calculate` tool'u Python `eval` kullanmaz; AST üzerinden sınırlı aritmetik çalıştırır.
- API anahtarları `.env` içinde tutulmalıdır.
- Testler gerçek API çağırmaz.
- Dış servis çağrılarında timeout vardır.

## Geliştirme Fikirleri

- HTTP transport örneği eklemek.
- Alternatif MCP client yaklaşımı göstermek.
- Tool çağrı loglarını ayrı bir gözlemlenebilirlik katmanına taşımak.
- Notebook'u adım adım workshop formatında yeniden üretmek.
