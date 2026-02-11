import { Card, Image, Text, Badge, Group, Stack } from "@mantine/core";
import type { ProofOfDelivery } from "../../types";

interface ProofCardProps {
  proof: ProofOfDelivery;
  onClick: () => void;
}

export function ProofCard({ proof, onClick }: ProofCardProps) {
  return (
    <Card shadow="sm" padding="sm" radius="md" withBorder onClick={onClick} style={{ cursor: "pointer" }}>
      <Card.Section>
        <Image
          src={proof.url}
          height={180}
          alt={`Proof for ${proof.packageId}`}
          fallbackSrc="https://placehold.co/300x180?text=No+Image"
        />
      </Card.Section>

      <Stack gap="xs" mt="sm">
        <Group justify="space-between">
          <Badge color="blue" variant="light" size="sm">
            {proof.packageId}
          </Badge>
          <Badge color="gray" variant="outline" size="sm">
            {proof.driverId}
          </Badge>
        </Group>
        <Text size="xs" c="dimmed">
          {new Date(proof.timestamp).toLocaleString()}
        </Text>
      </Stack>
    </Card>
  );
}
