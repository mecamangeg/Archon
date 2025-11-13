import { useQuery } from "@tanstack/react-query";
import { STALE_TIMES, DISABLED_QUERY_KEY } from "@/features/shared/config/queryPatterns";

interface SemanticSearchOptions {
  query: string;
  enabled: boolean;
  matchCount?: number;
}

interface SemanticSearchResult {
  source_id: string;
  similarity_score: number;
}

interface SemanticSearchResponse {
  results: SemanticSearchResult[];
}

/**
 * Hook for semantic search (AI-powered search)
 * Currently a stub implementation - full semantic search to be implemented
 */
export function useSemanticSearch(options: SemanticSearchOptions) {
  return useQuery({
    queryKey: options.enabled
      ? ["semantic-search", options.query, options.matchCount]
      : DISABLED_QUERY_KEY,
    queryFn: async (): Promise<SemanticSearchResponse> => {
      // Stub implementation - returns empty results
      // Full semantic search implementation will use vector embeddings
      return { results: [] };
    },
    enabled: options.enabled && options.query.trim().length > 0,
    staleTime: STALE_TIMES.frequent,
  });
}
