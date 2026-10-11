import { Modal, Image, Text, Badge, Group, Stack } from "@mantine/core";
import type { ProofOfDelivery } from "../../types";
import { useAuthedImage } from "../../hooks/useAuthedImage";

interface ProofDetailModalProps {
  proof: ProofOfDelivery | null;
  opened: boolean;
  onClose: () => void;
}

export function ProofDetailModal({ proof, opened, onClose }: ProofDetailModalProps) {
  const src = useAuthedImage(proof?.path);
  if (!proof) return null;

  return (
    <Modal opened={opened} onClose={onClose} size="lg" title="Proof of Delivery">
      <Stack gap="md">
        <Image
          src={src}
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

        <Group justify="space-between">
          <Stack gap={4}>
            <Text size="sm" fw={500}>Received by</Text>
            <Text size="sm">{proof.receivedBy ?? "Not recorded"}</Text>
          </Stack>
          <Stack gap={4}>
            <Text size="sm" fw={500}>Distance from drop</Text>
            <Text size="sm">
              {proof.distanceMeters != null ? `${Math.round(proof.distanceMeters)} m` : "No GPS"}
            </Text>
          </Stack>
        </Group>

        {proof.signature && (
          <Stack gap={4}>
            <Text size="sm" fw={500}>Signature</Text>
            <svg viewBox="0 0 320 120" style={{ width: "100%", height: 120, border: "1px solid #dee2e6", borderRadius: 6 }}>
              <path d={proof.signature} stroke="#1c7ed6" strokeWidth={2.5} fill="none" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </Stack>
        )}
      </Stack>
    </Modal>
  );
}
