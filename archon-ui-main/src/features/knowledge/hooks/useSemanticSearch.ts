/**
 * Semantic Search Hook
 * Provides semantic search functionality using RAG and vector embeddings
 */

import { useQuery } from "@tanstack/react-query";
import { knowledgeService } from "../services/knowledgeService";
import type { SearchOptions, SearchResultsResponse } from "../types";

interface UseSemanticSearchOptions {
  query: string;
  enabled?: boolean;
  matchCount?: number;
  sourceId?: string;
}

export const useSemanticSearch = ({ query, enabled = true, matchCount = 10, sourceId }: UseSemanticSearchOptions) => {
  return useQuery<SearchResultsResponse>({
    queryKey: ["semantic-search", query, sourceId, matchCount],
    queryFn: async () => {
      const options: SearchOptions = {
        query,
        match_count: matchCount,
        return_mode: "chunks",
      };

      if (sourceId) {
        options.source_id = sourceId;
      }

      return knowledgeService.searchKnowledgeBase(options);
    },
    enabled: enabled && query.trim().length > 0,
    staleTime: 30000, // Cache for 30 seconds
    gcTime: 5 * 60 * 1000, // Keep in cache for 5 minutes
  });
};
