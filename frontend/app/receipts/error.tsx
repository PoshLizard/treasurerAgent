"use client"; // error boundaries must be Client Components

import Notice, { buttonClass } from "../ui/notice";

// Shown when the backend can't be reached at all, for the list and for a single receipt
export default function ReceiptsError({ retry }: { retry: () => void }) {
  return (
    <div className="mx-auto max-w-3xl">
      <Notice title="Couldn't reach the server" message="It may be starting up. Try again in a minute.">
        <button type="button" onClick={() => retry()} className={buttonClass}>
          Try again
        </button>
      </Notice>
    </div>
  );
}
