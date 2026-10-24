import { createFileRoute } from "@tanstack/react-router";
import { MethodPage } from "@/components/method-page";

export const Route = createFileRoute("/method")({
  head: () => ({
    meta: [{ title: "Method — Sheldrake" }],
  }),
  component: MethodPage,
});
