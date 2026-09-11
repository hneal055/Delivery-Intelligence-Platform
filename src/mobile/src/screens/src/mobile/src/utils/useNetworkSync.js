import { useEffect, useState, useRef, useCallback } from 'react';
import NetInfo from '@react-native-community/netinfo';
import { getOfflineQueue, syncOfflineQueue } from './offlineQueue';

export function useNetworkSync(onSyncComplete) {
  const [isConnected, setIsConnected] = useState(true);
  const [isInternetReachable, setIsInternetReachable] = useState(true);
  const [isAutoSyncing, setIsAutoSyncing] = useState(false);
  const [pendingCount, setPendingCount] = useState(0);

  const prevReachableRef = useRef(true);

  const refreshPendingCount = useCallback(async () => {
    try {
      const q = await getOfflineQueue();
      setPendingCount(q.length);
      return q.length;
    } catch {
      setPendingCount(0);
      return 0;
    }
  }, []);

  useEffect(() => {
    refreshPendingCount();

    const unsubscribe = NetInfo.addEventListener(async (state) => {
      const connected = Boolean(state.isConnected);
      const reachable =
        state.isInternetReachable !== null ? Boolean(state.isInternetReachable) : connected;

      setIsConnected(connected);
      setIsInternetReachable(reachable);

      const justCameOnline = !prevReachableRef.current && reachable;
      prevReachableRef.current = reachable;

      if (justCameOnline) {
        console.log('[NetInfo] Connection restored. Evaluating offline queue...');
        const queue = await getOfflineQueue();

        if (queue.length > 0) {
          console.log(`[AutoSync] Auto-flushing ${queue.length} offline deliveries...`);
          setIsAutoSyncing(true);

          try {
            const result = await syncOfflineQueue();
            console.log(
              `[AutoSync] Completed. Synced: ${result.syncedCount}, Remaining: ${result.remainingCount}`
            );
            if (typeof onSyncComplete === 'function') {
              onSyncComplete(result);
            }
          } catch (err) {
            console.warn('[AutoSync] Background flush failed:', err.message);
          } finally {
            setIsAutoSyncing(false);
            refreshPendingCount();
          }
        }
      }
    });

    return () => unsubscribe();
  }, [onSyncComplete, refreshPendingCount]);

  return {
    isConnected,
    isInternetReachable,
    isAutoSyncing,
    pendingCount,
    refreshPendingCount,
  };
}

export default useNetworkSync;