/**
 * useApi Hook
 * ============
 * 
 * Generic hook for API calls with loading, error, and data states.
 * 
 * Features:
 * - Automatic loading state
 * - Error handling
 * - Data caching option
 * - Manual refetch
 */

import { useState, useCallback, useEffect, useRef } from 'react';

interface UseApiState<T> {
  data: T | null;
  isLoading: boolean;
  error: Error | null;
}

interface UseApiOptions {
  immediate?: boolean;  // Execute on mount
  cache?: boolean;      // Cache results
  cacheKey?: string;    // Custom cache key
}

interface UseApiReturn<T, P extends unknown[]> extends UseApiState<T> {
  execute: (...params: P) => Promise<T | null>;
  reset: () => void;
  setData: (data: T | null) => void;
}

// Simple in-memory cache
const cache = new Map<string, { data: unknown; timestamp: number }>();
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

export function useApi<T, P extends unknown[] = []>(
  apiFunction: (...params: P) => Promise<T>,
  options: UseApiOptions = {}
): UseApiReturn<T, P> {
  const { immediate = false, cache: useCache = false, cacheKey } = options;
  
  const [state, setState] = useState<UseApiState<T>>({
    data: null,
    isLoading: immediate,
    error: null,
  });

  const mountedRef = useRef(true);
  const apiFunctionRef = useRef(apiFunction);
  apiFunctionRef.current = apiFunction;

  const getCacheKey = useCallback((...params: P): string => {
    if (cacheKey) return cacheKey;
    return `${apiFunction.name || 'api'}-${JSON.stringify(params)}`;
  }, [cacheKey, apiFunction]);

  const getFromCache = useCallback((key: string): T | null => {
    if (!useCache) return null;
    
    const cached = cache.get(key);
    if (!cached) return null;
    
    if (Date.now() - cached.timestamp > CACHE_TTL) {
      cache.delete(key);
      return null;
    }
    
    return cached.data as T;
  }, [useCache]);

  const setToCache = useCallback((key: string, data: T): void => {
    if (!useCache) return;
    cache.set(key, { data, timestamp: Date.now() });
  }, [useCache]);

  const execute = useCallback(async (...params: P): Promise<T | null> => {
    const key = getCacheKey(...params);
    
    // Check cache first
    const cachedData = getFromCache(key);
    if (cachedData !== null) {
      setState({ data: cachedData, isLoading: false, error: null });
      return cachedData;
    }

    setState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      const data = await apiFunctionRef.current(...params);
      
      if (!mountedRef.current) return null;
      
      setToCache(key, data);
      setState({ data, isLoading: false, error: null });
      return data;
    } catch (error) {
      if (!mountedRef.current) return null;
      
      setState({
        data: null,
        isLoading: false,
        error: error instanceof Error ? error : new Error(String(error)),
      });
      return null;
    }
  }, [getCacheKey, getFromCache, setToCache]);

  const reset = useCallback(() => {
    setState({ data: null, isLoading: false, error: null });
  }, []);

  const setData = useCallback((data: T | null) => {
    setState(prev => ({ ...prev, data }));
  }, []);

  // Execute on mount if immediate
  useEffect(() => {
    if (immediate) {
      execute(...([] as unknown as P));
    }
  }, [immediate, execute]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      mountedRef.current = false;
    };
  }, []);

  return {
    ...state,
    execute,
    reset,
    setData,
  };
}

/**
 * usePaginatedApi Hook
 * 
 * Extended useApi for paginated data.
 */
interface PaginatedData<T> {
  items: T[];
  total: number;
  hasMore: boolean;
}

interface UsePaginatedApiReturn<T> {
  items: T[];
  total: number;
  hasMore: boolean;
  isLoading: boolean;
  error: Error | null;
  loadMore: () => Promise<void>;
  refresh: () => Promise<void>;
}

export function usePaginatedApi<T>(
  apiFunction: (skip: number, limit: number) => Promise<PaginatedData<T>>,
  limit: number = 20
): UsePaginatedApiReturn<T> {
  const [items, setItems] = useState<T[]>([]);
  const [total, setTotal] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const loadMore = useCallback(async () => {
    if (isLoading || !hasMore) return;

    setIsLoading(true);
    setError(null);

    try {
      const result = await apiFunction(items.length, limit);
      setItems(prev => [...prev, ...result.items]);
      setTotal(result.total);
      setHasMore(result.hasMore);
    } catch (e) {
      setError(e instanceof Error ? e : new Error(String(e)));
    } finally {
      setIsLoading(false);
    }
  }, [apiFunction, items.length, limit, isLoading, hasMore]);

  const refresh = useCallback(async () => {
    setItems([]);
    setHasMore(true);
    setIsLoading(true);
    setError(null);

    try {
      const result = await apiFunction(0, limit);
      setItems(result.items);
      setTotal(result.total);
      setHasMore(result.hasMore);
    } catch (e) {
      setError(e instanceof Error ? e : new Error(String(e)));
    } finally {
      setIsLoading(false);
    }
  }, [apiFunction, limit]);

  return {
    items,
    total,
    hasMore,
    isLoading,
    error,
    loadMore,
    refresh,
  };
}

export default useApi;





