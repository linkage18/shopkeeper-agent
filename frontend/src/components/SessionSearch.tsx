import { Search } from "lucide-react";
import { useState } from "react";

interface Props {
  sessions: { id: string; first_query: string; created_at: number }[];
  onSearch: (query: string) => void;
}

export function SessionSearch({ sessions, onSearch }: Props) {
  const [query, setQuery] = useState("");

  const filtered = query
    ? sessions.filter((s) => s.first_query.toLowerCase().includes(query.toLowerCase()))
    : sessions;

  const handleSearch = (val: string) => {
    setQuery(val);
    onSearch(val);
  };

  return (
    <div className="px-3 pb-2">
      <div className="relative">
        <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-porcelain-400" />
        <input
          type="text"
          placeholder="搜索历史会话..."
          value={query}
          onChange={(e) => handleSearch(e.target.value)}
          className="w-full rounded-md border border-porcelain-200 bg-porcelain-50 py-1.5 pl-8 pr-3 text-xs outline-none placeholder:text-porcelain-400 focus:border-kinpaku focus:ring-1 focus:ring-kinpaku"
        />
      </div>
      {query && (
        <div className="mt-1 max-h-40 overflow-y-auto rounded-md border border-porcelain-200 bg-white text-xs">
          {filtered.length === 0 && <p className="p-2 text-porcelain-400">无匹配会话</p>}
          {filtered.slice(0, 10).map((s) => (
            <button
              key={s.id}
              onClick={() => onSearch(s.id)}
              className="block w-full truncate px-2 py-1.5 text-left text-porcelain-700 hover:bg-porcelain-100"
            >
              {s.first_query || "(空)"}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
