import { createFileRoute } from "@tanstack/react-router";
import { Laboratory } from "@/components/laboratory";

export const Route = createFileRoute("/")({ component: Home });

function Home() {
  return <Laboratory />;
}
