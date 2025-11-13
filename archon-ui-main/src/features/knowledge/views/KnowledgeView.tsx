/**
 * Main Knowledge Base View Component
 * Orchestrates the knowledge base UI using vertical slice architecture
 */

import { useEffect, useMemo, useRef, useState } from "react";
import { useDebounce } from "@/features/shared/hooks/useDebounce";
import { useToast } from "@/features/shared/hooks/useToast";
import { CrawlingProgress } from "../../progress/components/CrawlingProgress";
import type { ActiveOperation } from "../../progress/types";
import { AddKnowledgeDialog } from "../components/AddKnowledgeDialog";
import { KnowledgeHeader } from "../components/KnowledgeHeader";
import { KnowledgeList } from "../components/KnowledgeList";
import { useInfiniteKnowledgeSummaries } from "../hooks/useKnowledgeQueries";
import { useSemanticSearch } from "../hooks/useSemanticSearch";
import { KnowledgeInspector } from "../inspector/components/KnowledgeInspector";
import type { KnowledgeItem, KnowledgeItemsFilter } from "../types";

export const KnowledgeView = () => {
  // View state
  const [viewMode, setViewMode] = useState<"grid" | "table">("grid");
  const [searchQuery, setSearchQuery] = useState("");
  const [searchMode, setSearchMode] = useState<"simple" | "semantic">("simple");
  const [typeFilter, setTypeFilter] = useState<"all" | "technical" | "business">("all");

  // Debounce search query to reduce API calls by 80-90%
  const debouncedSearchQuery = useDebounce(searchQuery, 500);

  // Dialog state
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [inspectorItem, setInspectorItem] = useState<KnowledgeItem | null>(null);
  const [inspectorInitialTab, setInspectorInitialTab] = useState<"documents" | "code">("documents");

  // Build filter object for API - memoize to prevent recreating on every render
  const filter = useMemo(() => {
    const f: Omit<KnowledgeItemsFilter, "page" | "per_page"> = {};

    if (debouncedSearchQuery) {
      f.search = debouncedSearchQuery;
    }

    if (typeFilter !== "all") {
      f.knowledge_type = typeFilter;
    }

    return f;
  }, [debouncedSearchQuery, typeFilter]);

  // Fetch knowledge summaries with infinite scroll - loads 20 items at a time
  const {
    items: allItems,
    total,
    isLoading,
    error,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    refetch,
    setActiveCrawlIds,
    activeOperations,
  } = useInfiniteKnowledgeSummaries(filter);

  // Semantic search (only when mode is semantic and query exists)
  const {
    data: semanticData,
    isLoading: semanticLoading,
    error: semanticError,
  } = useSemanticSearch({
    query: debouncedSearchQuery,
    enabled: searchMode === "semantic" && debouncedSearchQuery.trim().length > 0,
    matchCount: 20,
  });

  // Determine which items to display based on search mode
  let knowledgeItems = allItems || [];
  let totalItems = total || 0;

  // If semantic search is active and has results, group by source and filter items
  if (searchMode === "semantic" && semanticData?.results && semanticData.results.length > 0) {
    try {
      // Optimized: Pre-group semantic results by source_id to avoid O(n*m) nested filters
      const scoresBySource = new Map<string, { total: number; count: number }>();

      for (const result of semanticData.results) {
        if (result.source_id) {
          const existing = scoresBySource.get(result.source_id);
          if (existing) {
            existing.total += result.similarity_score || 0;
            existing.count += 1;
          } else {
            scoresBySource.set(result.source_id, {
              total: result.similarity_score || 0,
              count: 1,
            });
          }
        }
      }

      // Filter, map, and sort in a single efficient pass
      knowledgeItems = knowledgeItems
        .filter((item) => scoresBySource.has(item.source_id))
        .map((item) => {
          const scores = scoresBySource.get(item.source_id)!;
          return {
            ...item,
            relevanceScore: scores.total / scores.count,
          };
        })
        .sort((a, b) => (b.relevanceScore || 0) - (a.relevanceScore || 0));

      totalItems = knowledgeItems.length;
    } catch (error) {
      console.error("Error processing semantic search results:", error);
      // Fall back to showing all items without filtering if processing fails
    }
  }
  const hasActiveOperations = activeOperations.length > 0;
  const displayLoading = searchMode === "semantic" ? semanticLoading : isLoading;
  const displayError = searchMode === "semantic" ? semanticError : error;

  // Toast notifications
  const { showToast } = useToast();
  const previousOperations = useRef<ActiveOperation[]>([]);

  // Track crawl completions and errors for toast notifications
  useEffect(() => {
    // Find operations that just completed or failed
    const finishedOps = previousOperations.current.filter((prevOp) => {
      const currentOp = activeOperations.find((op) => op.operation_id === prevOp.operation_id);
      // Operation disappeared from active list - check its final status
      return (
        !currentOp &&
        ["crawling", "processing", "storing", "document_storage", "completed", "error", "failed"].includes(
          prevOp.status,
        )
      );
    });

    // Show toast for each finished operation
    finishedOps.forEach((op) => {
      // Check if it was an error or success
      if (op.status === "error" || op.status === "failed") {
        // Show error message with details
        const errorMessage = op.message || "Operation failed";
        showToast(`❌ ${errorMessage}`, "error", 7000);
      } else if (op.status === "completed") {
        // Show success message
        const message = op.message || "Operation completed";
        showToast(`✅ ${message}`, "success", 5000);
      }

      // Remove from active crawl IDs
      setActiveCrawlIds((prev) => prev.filter((id) => id !== op.operation_id));

      // Refetch summaries after any completion
      refetch();
    });

    // Update previous operations
    previousOperations.current = [...activeOperations];
  }, [activeOperations, showToast, refetch, setActiveCrawlIds]);

  const handleAddKnowledge = () => {
    setIsAddDialogOpen(true);
  };

  const handleViewDocument = (sourceId: string) => {
    // Find the item and open inspector to documents tab
    const item = knowledgeItems.find((k) => k.source_id === sourceId);
    if (item) {
      setInspectorInitialTab("documents");
      setInspectorItem(item);
    }
  };

  const handleViewCodeExamples = (sourceId: string) => {
    // Open the inspector to code examples tab
    const item = knowledgeItems.find((k) => k.source_id === sourceId);
    if (item) {
      setInspectorInitialTab("code");
      setInspectorItem(item);
    }
  };

  const handleDeleteSuccess = () => {
    // TanStack Query will automatically refetch
  };

  // Infinite scroll - load more items when scrolling near the bottom
  const loadMoreRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!loadMoreRef.current) return;
    if (!hasNextPage || isFetchingNextPage) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const first = entries[0];
        if (first.isIntersecting && hasNextPage && !isFetchingNextPage) {
          fetchNextPage();
        }
      },
      { threshold: 0.1 },
    );

    observer.observe(loadMoreRef.current);

    return () => observer.disconnect();
  }, [fetchNextPage, hasNextPage, isFetchingNextPage]);

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <KnowledgeHeader
        totalItems={totalItems}
        isLoading={displayLoading}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        searchMode={searchMode}
        onSearchModeChange={setSearchMode}
        typeFilter={typeFilter}
        onTypeFilterChange={setTypeFilter}
        viewMode={viewMode}
        onViewModeChange={setViewMode}
        onAddKnowledge={handleAddKnowledge}
      />

      {/* Main Content */}
      <div className="flex-1 overflow-auto px-6 pb-6">
        {/* Active Operations - Show at top when present */}
        {hasActiveOperations && (
          <div className="mb-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-white/90">Active Operations ({activeOperations.length})</h3>
              <div className="flex items-center gap-2 text-sm text-gray-400">
                <div className="w-2 h-2 bg-cyan-400 dark:bg-cyan-400 rounded-full animate-pulse" />
                Live Updates
              </div>
            </div>
            <CrawlingProgress onSwitchToBrowse={() => {}} />
          </div>
        )}

        {/* Knowledge Items List */}
        <KnowledgeList
          items={knowledgeItems}
          viewMode={viewMode}
          isLoading={displayLoading}
          error={displayError}
          onRetry={refetch}
          onViewDocument={handleViewDocument}
          onViewCodeExamples={handleViewCodeExamples}
          onDeleteSuccess={handleDeleteSuccess}
          activeOperations={activeOperations}
          onRefreshStarted={(progressId) => {
            // Add the progress ID to track it
            setActiveCrawlIds((prev) => [...prev, progressId]);
          }}
        />

        {/* Infinite scroll trigger - load more when visible */}
        {hasNextPage && !displayLoading && (
          <div ref={loadMoreRef} className="flex justify-center py-8">
            {isFetchingNextPage ? (
              <div className="flex items-center gap-2 text-sm text-gray-400">
                <div className="w-4 h-4 border-2 border-cyan-400/30 border-t-cyan-400 rounded-full animate-spin" />
                Loading more...
              </div>
            ) : (
              <div className="text-sm text-gray-500">Scroll to load more</div>
            )}
          </div>
        )}

        {/* Show total count when all items loaded */}
        {!hasNextPage && knowledgeItems.length > 0 && !displayLoading && (
          <div className="text-center py-4 text-sm text-gray-500">
            Showing all {totalItems} {totalItems === 1 ? "item" : "items"}
          </div>
        )}
      </div>

      {/* Dialogs */}
      <AddKnowledgeDialog
        open={isAddDialogOpen}
        onOpenChange={setIsAddDialogOpen}
        onSuccess={() => {
          setIsAddDialogOpen(false);
          refetch();
        }}
        onCrawlStarted={(progressId) => {
          // Add the progress ID to track it
          setActiveCrawlIds((prev) => [...prev, progressId]);
        }}
      />

      {/* Knowledge Inspector Modal */}
      {inspectorItem && (
        <KnowledgeInspector
          item={inspectorItem}
          open={!!inspectorItem}
          onOpenChange={(open) => {
            if (!open) setInspectorItem(null);
          }}
          initialTab={inspectorInitialTab}
        />
      )}
    </div>
  );
};
