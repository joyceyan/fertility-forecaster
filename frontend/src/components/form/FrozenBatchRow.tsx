interface Props {
  type: "egg" | "embryo";
  ageAtFreeze: number;
  count: number;
  onChangeAge: (v: number) => void;
  onChangeCount: (v: number) => void;
  onRemove: () => void;
  pgtTested?: boolean;
  onChangePgt?: (v: boolean) => void;
}

export default function FrozenBatchRow({
  type,
  ageAtFreeze,
  count,
  onChangeAge,
  onChangeCount,
  onRemove,
  pgtTested,
  onChangePgt,
}: Props) {
  const maxCount = type === "egg" ? 50 : 20;
  const countLabel = type === "egg" ? "eggs" : "embryos";

  return (
    <div className="flex items-end gap-2">
      <div className="flex-1">
        <label className="block text-xs text-stone-500">Age at freeze</label>
        <input
          type="number"
          min={18}
          max={45}
          value={ageAtFreeze || ""}
          placeholder="Age"
          onFocus={(e) => e.target.select()}
          onChange={(e) => onChangeAge(e.target.value ? +e.target.value : 0)}
          className="w-full rounded border border-stone-300 px-2 py-1 text-sm"
        />
      </div>
      <div className="flex-1">
        <label className="block text-xs text-stone-500"># {countLabel}</label>
        <input
          type="number"
          min={1}
          max={maxCount}
          value={count || ""}
          placeholder="#"
          onFocus={(e) => e.target.select()}
          onChange={(e) => onChangeCount(e.target.value ? +e.target.value : 0)}
          className="w-full rounded border border-stone-300 px-2 py-1 text-sm"
        />
      </div>
      {type === "embryo" && onChangePgt && (
        <label className="flex items-center gap-1 text-xs text-stone-500 whitespace-nowrap pb-1">
          <input
            type="checkbox"
            checked={pgtTested ?? false}
            onChange={(e) => onChangePgt(e.target.checked)}
            className="rounded border-stone-300"
          />
          PGT-A tested
        </label>
      )}
      <button
        type="button"
        onClick={onRemove}
        className="rounded p-1 text-stone-400 hover:text-red-500"
        aria-label="Remove batch"
      >
        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  );
}
