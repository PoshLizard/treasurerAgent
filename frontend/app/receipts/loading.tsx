import { SquaresLoader } from "../ui/loaders";

export default function Loading() {
  return (
    <div className="mx-auto max-w-3xl">
      <SquaresLoader label="Loading saved receipts" />
    </div>
  );
}
