import { useQuery } from "@tanstack/react-query";
import { STALE_TIMES, DISABLED_QUERY_KEY } from "@/features/shared/config/queryPatterns";
import { knowledgeService } from "../services/knowledgeService";

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
 * Hook for semantic search (AI-powered vector search)
 * Uses RAG query endpoint to search knowledge base using embeddings
 */
export function useSemanticSearch(options: SemanticSearchOptions) {
  return useQuery({
    queryKey: options.enabled
      ? ["semantic-search", options.query, options.matchCount]
      : DISABLED_QUERY_KEY,
    queryFn: async (): Promise<SemanticSearchResponse> => {
      // Call the backend semantic search API
      const response = await knowledgeService.searchKnowledgeBase({
        query: options.query,
        match_count: options.matchCount || 20,
        return_mode: "chunks", // Get chunks with similarity scores
      });

      // Group results by source_id and aggregate similarity scores
      const sourceScores = new Map<string, { total: number; count: number }>();

      for (const chunk of response.results) {
        if (chunk.source_id && chunk.similarity_score !== undefined) {
          const existing = sourceScores.get(chunk.source_id);
          if (existing) {
            existing.total += chunk.similarity_score;
            existing.count += 1;
          } else {
            sourceScores.set(chunk.source_id, {
              total: chunk.similarity_score,
              count: 1,
            });
          }
        }
      }

      // Convert to array format with averaged scores
      const results: SemanticSearchResult[] = Array.from(sourceScores.entries()).map(
        ([source_id, scores]) => ({
          source_id,
          similarity_score: scores.total / scores.count,
        }),
      );

      return { results };
    },
    enabled: options.enabled && options.query.trim().length > 0,
    staleTime: STALE_TIMES.frequent,
  });
}
