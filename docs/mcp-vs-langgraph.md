# MCP ve LangGraph Aynı Şey Değildir

MCP ve LangGraph genellikle aynı örneğin içinde kullanıldığı için birbirine karıştırılır. Bu projede özellikle bu ayrımı görünür yapıyoruz.

## MCP Ne Yapar?

MCP, bir uygulamanın LLM'e araç ve bağlam sunması için standart protokol sağlar.

MCP tarafındaki temel sorular:

- Server hangi tool'ları yayınlıyor?
- Tool input şeması nedir?
- Client tool listesini nasıl keşfediyor?
- Tool çağrısı hangi JSON-RPC mesajı ile gidiyor?
- Sonuç hangi formatta dönüyor?

Bu repo içinde MCP tarafını görmek için `mcp_server.py` ve `StdioMCPClient` sınıfına bakın.

## LangGraph Ne Yapar?

LangGraph, ajan uygulamasının adımlarını ve state geçişlerini yönetir.

LangGraph tarafındaki temel sorular:

- Kullanıcı mesajı hangi düğümde analiz ediliyor?
- Tool çağrısı ne zaman yapılıyor?
- Tool sonucu state içinde nasıl taşınıyor?
- Nihai cevap hangi düğümde üretiliyor?

Bu repo içinde LangGraph tarafını görmek için `build_graph` fonksiyonuna bakın.

## Birlikte Nasıl Çalışırlar?

```text
MCP server tool'ları yayınlar.
MCP client bu tool'ları keşfeder.
LangGraph ajanı kullanıcı isteğine göre tool seçer.
MCP client seçilen tool'u çağırır.
LangGraph tool sonucunu doğal dil cevabına dönüştürür.
```

## En Sık Karışıklık

Yanlış düşünce:

> LangGraph tool sağlar.

Daha doğru düşünce:

> MCP tool'ları standart şekilde sağlar; LangGraph bu tool'ları kullanan ajan akışını düzenler.

Yanlış düşünce:

> MCP bir ajan framework'üdür.

Daha doğru düşünce:

> MCP bir protokoldür. Ajan davranışını LangGraph, LangChain, OpenAI Agents SDK, Ollama kullanan lokal bir adapter veya başka bir orkestrasyon katmanı kurabilir.
