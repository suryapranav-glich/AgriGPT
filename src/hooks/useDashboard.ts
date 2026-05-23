// =============================================================================
// src/hooks/useDashboard.ts — React Query hook for dashboard metrics
// =============================================================================

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { dashboardApi, type DashboardMetrics } from "../lib/api";
import { useAuth } from "../contexts/AuthContext";

export const DASHBOARD_QUERY_KEY = ["dashboard", "metrics"];

/** Fetches live dashboard metrics from MongoDB via /dashboard/metrics */
export function useDashboardMetrics() {
  const { isAuthenticated } = useAuth();

  return useQuery<DashboardMetrics>({
    queryKey: DASHBOARD_QUERY_KEY,
    queryFn: dashboardApi.getMetrics,
    enabled: isAuthenticated,
    staleTime: 0,             // Force refetch on component mount / tab navigation
    refetchOnWindowFocus: true,
    retry: 2,
  });
}

/** Mutation to update dashboard fields (active crop, mandi price, etc.) */
export function useUpdateDashboardMetrics() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: dashboardApi.updateMetrics,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: DASHBOARD_QUERY_KEY });
    },
  });
}

/** Log a feature usage event to the activity feed */
export function useLogActivity() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: dashboardApi.logActivity,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: DASHBOARD_QUERY_KEY });
    },
  });
}
