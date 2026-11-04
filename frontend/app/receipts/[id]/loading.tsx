import { SquaresLoader } from "../../ui/loaders";

export default function Loading() {
  return (
    <div className="mx-auto max-w-6xl">
      <SquaresLoader label="Loading receipt" />
    </div>
  );
}
