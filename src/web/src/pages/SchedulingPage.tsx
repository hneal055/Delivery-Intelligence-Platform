import { useState } from 'react';
import { Title, Button, Group, Table, Badge, ActionIcon, Menu, Text, Container } from '@mantine/core';
import { IconList, IconPlus, IconDotsVertical, IconTrash, IconUserPlus } from '@tabler/icons-react';
import { useDispatch } from '../hooks/useDispatch';
import { CreateJobModal } from '../components/dispatch/CreateJobModal';
import { AssignmentModal } from '../components/dispatch/AssignmentModal';
import type { DispatchJob } from '../types';

export function SchedulingPage() {
  const { useJobs, deleteJob, updateJobStatus } = useDispatch();
  const { data: jobs = [], isLoading } = useJobs();
  
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [assignmentModalOpen, setAssignmentModalOpen] = useState(false);
  const [selectedJob, setSelectedJob] = useState<DispatchJob | null>(null);

  const openAssignment = (job: DispatchJob) => {
    setSelectedJob(job);
    setAssignmentModalOpen(true);
  };

  const handleStatusChange = (jobId: string, status: string) => {
    updateJobStatus.mutate({ jobId, status });
  };

  const handleDelete = (jobId: string) => {
      if (confirm('Are you sure you want to delete this job?')) {
          deleteJob.mutate(jobId);
      }
  };

  const rows = jobs.map((job) => (
    <Table.Tr key={job.id}>
      <Table.Td>{job.title}</Table.Td>
      <Table.Td>{job.scheduled_at ? new Date(job.scheduled_at).toLocaleString() : "—"}</Table.Td>
      <Table.Td>
        {job.driver_id ? (
           <Badge color="blue">Assigned</Badge>
        ) : (
           <Badge color="yellow">Unassigned</Badge>
        )}
      </Table.Td>
      <Table.Td>
        <Badge variant="outline">{job.status}</Badge>
      </Table.Td>
      <Table.Td>
        <Group gap="xs">
            {!job.driver_id && (
                <Button size="xs" variant="light" leftSection={<IconUserPlus size={14} />} onClick={() => openAssignment(job)}>
                    Assign
                </Button>
            )}
            
            <Menu shadow="md" width={200}>
                <Menu.Target>
                    <ActionIcon variant="subtle" color="gray">
                        <IconDotsVertical size={16} />
                    </ActionIcon>
                </Menu.Target>

                <Menu.Dropdown>
                    <Menu.Label>Status</Menu.Label>
                    <Menu.Item onClick={() => handleStatusChange(job.id, 'pending')}>Pending</Menu.Item>
                    <Menu.Item onClick={() => handleStatusChange(job.id, 'in_progress')}>In Progress</Menu.Item>
                    <Menu.Item onClick={() => handleStatusChange(job.id, 'completed')}>Completed</Menu.Item>
                    <Menu.Item onClick={() => handleStatusChange(job.id, 'cancelled')}>Cancelled</Menu.Item>
                    
                    <Menu.Divider />
                    
                    <Menu.Label>Danger</Menu.Label>
                    <Menu.Item color="red" leftSection={<IconTrash size={14} />} onClick={() => handleDelete(job.id)}>
                        Delete Job
                    </Menu.Item>
                </Menu.Dropdown>
            </Menu>
        </Group>
      </Table.Td>
    </Table.Tr>
  ));

  return (
    <Container size="xl" py="xl">
        <Group justify="space-between" mb="lg">
            <Title order={2}>Job Scheduling</Title>
            <Button leftSection={<IconPlus size={20} />} onClick={() => setCreateModalOpen(true)}>
                Create Job
            </Button>
        </Group>

        <Table striped highlightOnHover withTableBorder>
            <Table.Thead>
                <Table.Tr>
                    <Table.Th>Title</Table.Th>
                    <Table.Th>Scheduled</Table.Th>
                    <Table.Th>Assignment</Table.Th>
                    <Table.Th>Status</Table.Th>
                    <Table.Th>Actions</Table.Th>
                </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
                {isLoading ? (
                    <Table.Tr>
                        <Table.Td colSpan={5} align="center">Loading jobs...</Table.Td>
                    </Table.Tr>
                ) : rows.length > 0 ? (
                    rows
                ) : (
                    <Table.Tr>
                        <Table.Td colSpan={5} align="center">
                             <Group gap="xs" justify="center" c="dimmed" p="xl">
                                <IconList />
                                <Text>No jobs scheduled</Text>
                             </Group>
                        </Table.Td>
                    </Table.Tr>
                )}
            </Table.Tbody>
        </Table>

        <CreateJobModal 
            opened={createModalOpen} 
            onClose={() => setCreateModalOpen(false)} 
        />
        
        <AssignmentModal 
            job={selectedJob} 
            opened={assignmentModalOpen} 
            onClose={() => { setAssignmentModalOpen(false); setSelectedJob(null); }} 
        />
    </Container>
  );
}
