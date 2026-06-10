# Medium Taslağı: MCP ve LangGraph ile Türkçe Öğretici Ajan Projesi

## Başlık Önerisi

MCP ve LangGraph Kafasını Netleştirelim: Python ile Tool Kullanan Ajan Demo'su

## Giriş

LLM uygulamaları büyüdükçe iki ihtiyaç ortaya çıkar:

1. Modele dış dünyaya erişen araçlar vermek.
2. Modelin bu araçları ne zaman ve nasıl kullanacağını yönetmek.

Bu yazıda MCP ve LangGraph'ı aynı demo içinde kullanacağız ama rollerini özellikle ayrı tutacağız.

## Ana Fikir

MCP, tool entegrasyonunu standartlaştırır. LangGraph, ajan akışını düzenler.

```text
MCP       = tool protokolü
LangGraph = ajan orkestrasyonu
```

## Proje Senaryosu

Küçük bir araştırma ve öğrenme asistanı kuruyoruz. Ajan şu tool'ları kullanabiliyor:

- Hava durumu sorgulama
- Web araması
- Güvenli hesaplama
- Birim dönüşümü
- Metin analizi
- Öğrenme planı oluşturma

Bu çeşitlilik bilinçli: MCP'nin yalnızca web API çağırmak olmadığını, lokal deterministik fonksiyonları da aynı standartla sunabildiğini gösteriyor.

## Bölüm 1: Tool Önce Normal Fonksiyondur

`tools.py` dosyasında her tool test edilebilir saf Python fonksiyonu olarak başlar. Bu yaklaşım server kodunu sade tutar ve dış API çağırmadan test yazmayı kolaylaştırır.

## Bölüm 2: FastMCP ile Server

`mcp_server.py`, bu fonksiyonları `@mcp.tool()` ile yayınlar. Burada önemli nokta server'ın ajan olmamasıdır. Server yalnızca kabiliyet sunar.

## Bölüm 3: Client Handshake ve Tool Discovery

`mcp_client.py` önce server'ı STDIO üzerinden başlatır. Ardından:

1. `initialize`
2. `initialized`
3. `tools/list`
4. `tools/call`

adımlarını çalıştırır.

`tools/list` bu yazının kritik noktalarından biridir. Çünkü client tool'ları prompt içine elle yazmak yerine server'dan keşfeder.

## Bölüm 4: LangGraph ile Ajan Akışı

LangGraph tarafında iki düğüm var:

- `route`: Kullanıcı isteğini analiz eder ve gerekirse MCP tool seçer.
- `respond`: Tool sonucunu kullanıcıya Türkçe ve anlaşılır biçimde açıklar.

Bu yapı basit ama öğreticidir. Daha karmaşık ajanlarda memory, human-in-the-loop veya çok adımlı planlama eklenebilir.

## Bölüm 5: LLM Router'a Her Şeyi Bırakmayın

Demo sırasında özellikle lokal LLM kullandığımız için bazı sınırlar görünür hale gelir. Model bazen doğru tool'u seçse bile parametreyi eksik çıkarabilir. Bazen de tool sonucunu Türkçeye çevirirken gereksiz yorum ekleyebilir.

Bu yüzden projede hibrit bir yaklaşım kullanıyoruz:

- `Bursa hava durumu` gibi net kalıplar deterministik route ile doğrudan `get_weather` tool'una gider.
- `8+5 kaç yapar` veya `(10+71) karekökü nedir` gibi matematik soruları LLM'e hesaplatılmaz; `calculate` tool'u çalışır.
- Hesaplama sonucu tekrar LLM'e yorumlatılmaz, doğrudan formatlanır.
- Hava durumu hataları kısa Türkçe mesajla normalize edilir.

Bu pratik şunu gösterir: MCP tool'ları standartlaştırır, LangGraph akışı yönetir, fakat güvenilir ajan davranışı için routing ve cevap formatlama tasarımı hâlâ önemlidir.

## Bölüm 6: Testler

Testler OpenAI, Ollama veya dış API çağırmaz. Bunun yerine:

- `calculate`
- `convert_units`
- `analyze_text`
- `create_learning_roadmap`
- client helper fonksiyonları

doğrudan test edilir.

Bu sayede demo güvenilir kalır.

## Sonuç

MCP ve LangGraph aynı problemi çözmez; birbirini tamamlar.

MCP sayesinde tool entegrasyonları standartlaşır. LangGraph sayesinde ajan davranışı okunabilir ve yönetilebilir hale gelir.

Bu ayrımı net kurduğumuzda LLM uygulamalarını daha modüler, test edilebilir ve öğretilebilir şekilde geliştirebiliriz.
