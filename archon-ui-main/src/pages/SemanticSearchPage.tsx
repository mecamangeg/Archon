/**
 * Semantic Search Page
 * Dedicated page for testing and using semantic search with full parameter control
 */

import { useState } from "react";
import { Button, Input } from "../features/ui/primitives";
import { Search, Sparkles, Copy, CheckCircle } from "lucide-react";
import { knowledgeService } from "../features/knowledge/services/knowledgeService";
import type { SearchOptions, SearchResultsResponse } from "../features/knowledge/types";

export const SemanticSearchPage = () => {
  const [query, setQuery] = useState("");
  const [matchCount, setMatchCount] = useState(10);
  const [returnMode, setReturnMode] = useState<"pages" | "chunks">("chunks");
  const [sourceId, setSourceId] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState<SearchResultsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const handleSearch = async () => {
    if (!query.trim()) {
      setError("Please enter a search query");
      return;
    }

    setIsLoading(true);
    setError(null);
    setResults(null);

    try {
      const options: SearchOptions = {
        query: query.trim(),
        match_count: matchCount,
        return_mode: returnMode,
      };

      if (sourceId.trim()) {
        options.source_id = sourceId.trim();
      }

      const response = await knowledgeService.searchKnowledgeBase(options);
      setResults(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to perform search");
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopyCommand = () => {
    const cmd = `curl -X POST "http://localhost:8181/api/knowledge-items/search" -H "Content-Type: application/json" -d '${JSON.stringify({
      query,
      match_count: matchCount,
      return_mode: returnMode,
      ...(sourceId.trim() && { source_id: sourceId.trim() }),
    })}'`;

    navigator.clipboard.writeText(cmd);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSearch();
    }
  };

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-7xl mx-auto p-8 space-y-6">
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <Sparkles className="h-8 w-8 text-blue-600 dark:text-blue-400" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Semantic Search Lab</h1>
            <p className="text-sm text-gray-500 dark:text-zinc-400 mt-1">
              Direct access to vector search with full parameter control
            </p>
          </div>
        </div>

        {/* Search Controls */}
        <div className="space-y-6">
          {/* Search Input */}
          <div className="bg-white dark:bg-black/30 border border-gray-200 dark:border-white/10 shadow-sm rounded-lg p-6 space-y-4">
            <label className="block">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">
                Search Query
              </span>
              <Input
                type="text"
                placeholder="Enter your semantic search query..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyPress={handleKeyPress}
                className="bg-gray-50 dark:bg-black/30 border-gray-300 dark:border-white/10"
              />
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
                Tip: Use 2-5 keywords for best results (e.g., "claude code skills")
              </p>
            </label>

            {/* Parameters Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <label className="block">
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">
                  Match Count
                </span>
                <Input
                  type="number"
                  min="1"
                  max="50"
                  value={matchCount}
                  onChange={(e) => setMatchCount(parseInt(e.target.value) || 10)}
                  className="bg-gray-50 dark:bg-black/30 border-gray-300 dark:border-white/10"
                />
              </label>

              <label className="block">
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">
                  Return Mode
                </span>
                <select
                  value={returnMode}
                  onChange={(e) => setReturnMode(e.target.value as "pages" | "chunks")}
                  className="w-full px-3 py-2 bg-white dark:bg-black/30 border border-gray-200 dark:border-white/10 shadow-sm rounded-md text-white focus:outline-none focus:ring-2 focus:ring-cyan-500/50"
                >
                  <option value="chunks">Chunks (granular)</option>
                  <option value="pages">Pages (full context)</option>
                </select>
              </label>

              <label className="block">
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">
                  Source ID (optional)
                </span>
                <Input
                  type="text"
                  placeholder="Filter by source..."
                  value={sourceId}
                  onChange={(e) => setSourceId(e.target.value)}
                  className="bg-gray-50 dark:bg-black/30 border-gray-300 dark:border-white/10"
                />
              </label>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-3">
              <Button
                onClick={handleSearch}
                disabled={isLoading || !query.trim()}
                className="flex-1 bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-600 hover:to-blue-600 text-white font-medium"
              >
                <Search className="w-4 h-4 mr-2" />
                {isLoading ? "Searching..." : "Search"}
              </Button>

              <Button
                onClick={handleCopyCommand}
                variant="outline"
                className="border-white/10 text-gray-700 dark:text-gray-300 hover:bg-white/5"
              >
                {copied ? (
                  <>
                    <CheckCircle className="w-4 h-4 mr-2" />
                    Copied!
                  </>
                ) : (
                  <>
                    <Copy className="w-4 h-4 mr-2" />
                    Copy CLI Command
                  </>
                )}
              </Button>
            </div>
          </div>

          {/* Error Display */}
          {error && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
              <p className="text-red-400 text-sm">{error}</p>
            </div>
          )}

          {/* Results Display */}
          {results && (
            <div className="space-y-4">
              {/* Results Summary */}
              <div className="bg-white dark:bg-black/30 border border-gray-200 dark:border-white/10 shadow-sm rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Results</h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                      Found {results.results?.length || 0} matches
                      {results.total_found !== undefined && ` (total: ${results.total_found})`}
                    </p>
                  </div>
                  <div className="flex gap-2 text-xs">
                    {results.search_mode && (
                      <span className="px-2 py-1 bg-cyan-500/20 text-cyan-400 rounded">
                        {results.search_mode}
                      </span>
                    )}
                    {results.reranking_applied && (
                      <span className="px-2 py-1 bg-purple-500/20 text-purple-400 rounded">
                        reranked
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Results List */}
              {results.results && results.results.length > 0 ? (
                <div className="space-y-3">
                  {results.results.map((result, index) => (
                    <div
                      key={index}
                      className="bg-white dark:bg-black/30 border border-gray-200 dark:border-white/10 shadow-sm rounded-lg p-4 hover:border-cyan-500/30 transition-colors"
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-xs font-mono text-gray-500">#{index + 1}</span>
                            {result.similarity_score !== undefined && (
                              <span className="px-2 py-0.5 bg-cyan-500/20 text-cyan-400 rounded text-xs font-medium">
                                {(result.similarity_score * 100).toFixed(1)}% match
                              </span>
                            )}
                            {(result as any).rerank_score !== undefined && (
                              <span className="px-2 py-0.5 bg-purple-500/20 text-purple-400 rounded text-xs font-medium">
                                {((result as any).rerank_score * 100).toFixed(1)}% relevance
                              </span>
                            )}
                          </div>
                          {result.title && (
                            <h4 className="text-white font-medium mb-1">{result.title}</h4>
                          )}
                          {result.metadata?.source_id && (
                            <p className="text-xs text-gray-500 font-mono">
                              Source: {result.metadata.source_id}
                            </p>
                          )}
                        </div>
                      </div>
                      <div className="bg-gray-100 dark:bg-black/50 rounded p-3 mt-2">
                        <pre className="text-xs text-gray-700 dark:text-gray-300 whitespace-pre-wrap font-mono">
                          {result.content.substring(0, 500)}
                          {result.content.length > 500 && "..."}
                        </pre>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="bg-white dark:bg-black/30 border border-gray-200 dark:border-white/10 shadow-sm rounded-lg p-8 text-center">
                  <p className="text-gray-500 dark:text-gray-400">No results found for your query</p>
                </div>
              )}

              {/* Raw JSON Toggle */}
              <details className="bg-white dark:bg-black/30 border border-gray-200 dark:border-white/10 shadow-sm rounded-lg">
                <summary className="px-4 py-3 cursor-pointer text-sm font-medium text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white">
                  View Raw JSON Response
                </summary>
                <div className="border-t border-white/10 p-4 bg-black/50">
                  <pre className="text-xs text-gray-700 dark:text-gray-300 overflow-auto">
                    {JSON.stringify(results, null, 2)}
                  </pre>
                </div>
              </details>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
