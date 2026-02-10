import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  listJobs,
  createJob,
  assignJob,
  updateJobStatus,
  deleteJob,
  getAvailability,
  setAvailability
} from '../api/dispatch';
import type { 
  DispatchJobCreate, 
  DriverAvailabilityCreate 
} from '../types';

export function useDispatch() {
  const queryClient = useQueryClient();

  // Jobs Query
  const useJobs = (start_time?: string, end_time?: string, driver_id?: string, status?: string) => {
    return useQuery({
      queryKey: ['jobs', { start_time, end_time, driver_id, status }],
      queryFn: () => listJobs(start_time, end_time, driver_id, status),
    });
  };

  // Availability Query
  const useAvailability = (start_date: string, end_date: string, driver_id?: string) => {
    return useQuery({
      queryKey: ['availability', { start_date, end_date, driver_id }],
      queryFn: () => getAvailability(start_date, end_date, driver_id),
    });
  };

  // Mutations
  const createJobMutation = useMutation({
    mutationFn: (job: DispatchJobCreate) => createJob(job),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
    },
  });

  const assignJobMutation = useMutation({
    mutationFn: ({ jobId, driverId }: { jobId: string; driverId: string }) => assignJob(jobId, driverId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
    },
  });

  const updateJobStatusMutation = useMutation({
    mutationFn: ({ jobId, status }: { jobId: string; status: string }) => updateJobStatus(jobId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
    },
  });
  
  const deleteJobMutation = useMutation({
      mutationFn: (jobId: string) => deleteJob(jobId),
      onSuccess: () => {
          queryClient.invalidateQueries({ queryKey: ['jobs'] });
      }
  });

  const setAvailabilityMutation = useMutation({
    mutationFn: (availability: DriverAvailabilityCreate) => setAvailability(availability),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['availability'] });
    },
  });

  return {
    useJobs,
    useAvailability,
    createJob: createJobMutation,
    assignJob: assignJobMutation,
    updateJobStatus: updateJobStatusMutation,
    deleteJob: deleteJobMutation,
    setAvailability: setAvailabilityMutation,
  };
}
