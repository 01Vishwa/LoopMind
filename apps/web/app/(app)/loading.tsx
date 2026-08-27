import { BlockSkeleton } from "@/components/shared/DataStates";

/** Route-transition fallback for the app shell. */
export default function AppLoading() {
  return <BlockSkeleton className="p-6 max-w-2xl" lines={6} />;
}
