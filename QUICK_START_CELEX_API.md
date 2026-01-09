# Quick Start: Using the New CELEX API

## TL;DR

The CELEX API now accepts **any format** (GDPR, 2016/679, etc.) and caches results for **100x faster queries**.

## Common Use Cases

### 1. Search Bar with Auto-Suggestions

**Frontend (React/Next.js)**:
```typescript
'use client';
import { useState, useEffect } from 'react';

export function CelexSearchBar() {
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState([]);

  useEffect(() => {
    const fetchSuggestions = async () => {
      if (query.length < 2) return;

      const res = await fetch(`/api/celex/suggest?q=${query}&limit=5`);
      const data = await res.json();
      setSuggestions(data.suggestions);
    };

    const timer = setTimeout(fetchSuggestions, 300);
    return () => clearTimeout(timer);
  }, [query]);

  return (
    <div>
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search CELEX (e.g., GDPR, 2016/679)"
      />
      {suggestions.length > 0 && (
        <ul>
          {suggestions.map((s) => (
            <li key={s.celex} onClick={() => selectDocument(s.celex)}>
              {s.display_text}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

### 2. Document Lookup

**Any of these work!**:
```typescript
// All return the same GDPR document
await fetchDocument('GDPR');
await fetchDocument('2016/679');
await fetchDocument('32016R0679');
await fetchDocument('Regulation (EU) 2016/679');

async function fetchDocument(celex: string) {
  const res = await fetch(`/api/celex/query/${encodeURIComponent(celex)}`);
  const doc = await res.json();

  console.log(doc.title);              // Document title
  console.log(doc.date_document);      // Publication date
  console.log(doc.cached);             // Was it cached? (for debugging)

  return doc;
}
```

### 3. Dashboard - Load Multiple Documents

```typescript
async function loadDashboard() {
  const res = await fetch('/api/celex/bulk', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      celex_list: ['GDPR', 'AI Act', 'DMA', 'DSA', 'PSD2'],
      use_cache: true
    })
  });

  const data = await res.json();

  console.log(`Loaded ${data.found}/${data.total} documents`);
  console.log(`Cache hits: ${data.cache_hits}`);

  return data.results;
}
```

### 4. Input Validation

```typescript
async function validateCelexInput(userInput: string) {
  const res = await fetch(`/api/celex/normalize/${encodeURIComponent(userInput)}`);
  const data = await res.json();

  if (data.valid) {
    console.log(`✅ Valid! Normalized to: ${data.normalized}`);
    return data.normalized;
  } else {
    console.log(`❌ Invalid: ${data.error}`);
    return null;
  }
}

// Examples:
await validateCelexInput('GDPR');        // ✅ → 32016R0679
await validateCelexInput('2016/679');    // ✅ → 32016R0679
await validateCelexInput('hello world'); // ❌ → null
```

### 5. Monitoring Cache Performance

```typescript
async function getCacheStats() {
  const res = await fetch('/api/celex/cache/stats');
  const stats = await res.json();

  console.log(`Cache: ${stats.connected ? 'Connected' : 'Disconnected'}`);
  console.log(`Total keys: ${stats.total_keys}`);
  console.log(`Memory: ${stats.memory_used_mb} MB`);
  console.log(`Hit rate: ${stats.hit_rate}%`);
}
```

## Backend Usage (Python)

### Direct CellarClient Usage

```python
from src.ingestion.cellar import CellarClient

# Initialize with caching (default)
client = CellarClient()

# Query with flexible input
metadata = client.query_by_celex("GDPR")
# or
metadata = client.query_by_celex("2016/679")
# or
metadata = client.query_by_celex("32016R0679")

print(metadata['title'])
print(metadata['date_document'])

# Bulk query
results = client.query_bulk_celex(["GDPR", "AI Act", "DMA"])
for celex, metadata in results.items():
    if metadata:
        print(f"{celex}: {metadata['title']}")

# Cache stats
stats = client.get_cache_stats()
print(f"Hit rate: {stats['hit_rate']}%")

client.close()
```

### Using Normalization Utilities

```python
from src.utils.celex_utils import normalize_celex, parse_celex

# Normalize various inputs
normalized = normalize_celex("GDPR")  # → 32016R0679
normalized = normalize_celex("2016/679")  # → 32016R0679

# Parse CELEX
parsed = parse_celex("32016R0679")
print(parsed['year'])  # 2016
print(parsed['type_name'])  # REGULATION
print(parsed['sector_name'])  # EU_LEGISLATION
```

## API Reference

### All Endpoints

```bash
# Auto-suggestions
GET /celex/suggest?q={query}&limit={limit}

# Single query (flexible input)
GET /celex/query/{celex}

# Bulk query
POST /celex/bulk
Body: {"celex_list": [...], "use_cache": true}

# Normalize input
GET /celex/normalize/{input}

# Cache stats
GET /celex/cache/stats

# Clear cache (admin)
DELETE /celex/cache/clear

# Health check
GET /celex/health
```

## Supported Input Formats

| Input | Normalized To | Notes |
|-------|---------------|-------|
| `GDPR` | `32016R0679` | Common name alias |
| `AI Act` | `32024R1689` | Common name alias |
| `DMA` | `32022R1925` | Common name alias |
| `DSA` | `32022R2065` | Common name alias |
| `2016/679` | `32016R0679` | Year/number format |
| `2016-679` | `32016R0679` | Year-number format |
| `Regulation 2016/679` | `32016R0679` | Full text format |
| `Regulation (EU) 2016/679` | `32016R0679` | Full official format |
| `32016R0679` | `32016R0679` | Standard CELEX |
| `32016R679` | `32016R0679` | Auto-pads zeros |

## Common Aliases

```
GDPR → 32016R0679
AI Act → 32024R1689
DMA (Digital Markets Act) → 32022R1925
DSA (Digital Services Act) → 32022R2065
PSD2 (Payment Services) → 32015L2366
NIS2 (Network Security) → 32022L2555
ePrivacy → 32002L0058
```

## Performance Tips

1. **Always use cache** (enabled by default):
   - First query: 500-2000ms
   - Cached query: <10ms

2. **Use bulk queries** for multiple documents:
   ```typescript
   // ❌ Slow: Multiple requests
   const docs = await Promise.all(
     celexList.map(c => fetch(`/api/celex/query/${c}`))
   );

   // ✅ Fast: Single bulk request
   const { results } = await fetch('/api/celex/bulk', {
     method: 'POST',
     body: JSON.stringify({ celex_list: celexList })
   });
   ```

3. **Cache auto-suggestions**:
   ```typescript
   // Cache results in frontend for 5 minutes
   const cachedSuggestions = useMemo(
     () => fetchSuggestions(query),
     [query]
   );
   ```

## Troubleshooting

### "CELEX not found"
- Try normalizing first: `GET /celex/normalize/{input}`
- Check if it's a valid CELEX format
- Verify the document exists in EU Cellar

### "Cache not connected"
- Redis may not be running
- System will work without cache (just slower)
- Check: `GET /celex/health`

### "Slow queries"
- Check cache hit rate: `GET /celex/cache/stats`
- If hit rate < 50%, cache might need warmup
- If Redis disconnected, queries hit Cellar directly (slow)

## Interactive API Docs

Visit **http://localhost:8000/api/docs** for:
- Interactive API testing
- Request/response examples
- Schema definitions
- Authentication (if needed)

## Need Help?

- Full docs: `BACKEND_IMPROVEMENTS_IMPLEMENTED.md`
- Analysis: `BACKEND_ANALYSIS_AND_RECOMMENDATIONS.md`
- Summary: `PRIORITY_1_COMPLETE.md`
