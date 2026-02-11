import { useState, useMemo } from "react";
import { Title, Container, SimpleGrid, Text, Center, Stack, Loader } from "@mantine/core";
import { IconPhoto } from "@tabler/icons-react";
import { useDeliveryProofs } from "../hooks/useDeliveryProofs";
import { ProofCard } from "../components/delivery/ProofCard";
import { ProofDetailModal } from "../components/delivery/ProofDetailModal";
import { ProofFilterBar } from "../components/delivery/ProofFilterBar";
import type { ProofOfDelivery } from "../types";

export function ProofGalleryPage() {
  const { data: proofs = [], isLoading } = useDeliveryProofs();
  const [selectedProof, setSelectedProof] = useState<ProofOfDelivery | null>(null);
  const [search, setSearch] = useState("");
  const [dateRange, setDateRange] = useState<string | null>(null);

  const filteredProofs = useMemo(() => {
    let result = proofs;

    if (search) {
      const q = search.toLowerCase();
      result = result.filter(
        (p) =>
          p.packageId.toLowerCase().includes(q) ||
          p.driverId.toLowerCase().includes(q)
      );
    }

    if (dateRange && dateRange !== "all") {
      const now = new Date();
      let cutoff: Date;
      if (dateRange === "today") {
        cutoff = new Date(now.getFullYear(), now.getMonth(), now.getDate());
      } else if (dateRange === "7days") {
        cutoff = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
      } else {
        cutoff = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
      }
      result = result.filter((p) => new Date(p.timestamp) >= cutoff);
    }

    return result;
  }, [proofs, search, dateRange]);

  return (
    <Container size="xl" py="xl">
      <Stack gap="lg">
        <Title order={2}>Proof of Delivery Gallery</Title>

        <ProofFilterBar
          search={search}
          onSearchChange={setSearch}
          dateRange={dateRange}
          onDateRangeChange={setDateRange}
        />

        {isLoading ? (
          <Center py="xl">
            <Loader />
          </Center>
        ) : filteredProofs.length > 0 ? (
          <SimpleGrid cols={{ base: 1, sm: 2, md: 3, lg: 4 }}>
            {filteredProofs.map((proof) => (
              <ProofCard
                key={proof.filename}
                proof={proof}
                onClick={() => setSelectedProof(proof)}
              />
            ))}
          </SimpleGrid>
        ) : (
          <Center py="xl">
            <Stack align="center" gap="xs" c="dimmed">
              <IconPhoto size={48} stroke={1.5} />
              <Text>No proof of delivery images found</Text>
            </Stack>
          </Center>
        )}
      </Stack>

      <ProofDetailModal
        proof={selectedProof}
        opened={!!selectedProof}
        onClose={() => setSelectedProof(null)}
      />
    </Container>
  );
}
