import { Modal, Image, Text, Badge, Group, Stack } from "@mantine/core";
import type { ProofOfDelivery } from "../../types";

interface ProofDetailModalProps {
  proof: ProofOfDelivery | null;
  opened: boolean;
  onClose: () => void;
}

export function ProofDetailModal({ proof, opened, onClose }: ProofDetailModalProps) {
  if (!proof) return null;

  return (
    <Modal opened={opened} onClose={onClose} size="lg" title="Proof of Delivery">
      <Stack gap="md">
        <Image
          src={proof.url}
          alt={`Proof for ${proof.packageId}`}
          radius="md"
          fallbackSrc="https://placehold.co/600x400?text=No+Image"
        />

        <Group justify="space-between">
          <Stack gap={4}>
            <Text size="sm" fw={500}>Package ID</Text>
            <Badge color="blue" variant="light" size="lg">{proof.packageId}</Badge>
          </Stack>
          <Stack gap={4}>
            <Text size="sm" fw={500}>Driver ID</Text>
            <Badge color="gray" variant="outline" size="lg">{proof.driverId}</Badge>
          </Stack>
          <Stack gap={4}>
            <Text size="sm" fw={500}>Captured</Text>
            <Text size="sm">{new Date(proof.timestamp).toLocaleString()}</Text>
          </Stack>
        </Group>
      </Stack>
    </Modal>
  );
}
