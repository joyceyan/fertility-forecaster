import { useState } from "react";
import type { DraftFormState, FrozenEggBatch, FrozenEmbryoBatch } from "../../api/types";
import FrozenBatchRow from "./FrozenBatchRow";

interface Props {
  form: DraftFormState;
  onChange: (updates: Partial<DraftFormState>) => void;
}

export default function FrozenStorageChoiceVariant({ form, onChange }: Props) {
  const [showEggs, setShowEggs] = useState(form.frozen_egg_batches.length > 0);
  const [showEmbryos, setShowEmbryos] = useState(form.frozen_embryo_batches.length > 0);

  const addEggBatch = () => {
    if (form.frozen_egg_batches.length >= 5) return;
    onChange({
      frozen_egg_batches: [
        ...form.frozen_egg_batches,
        { age_at_freeze: 0, num_eggs: 0 },
      ],
    });
  };

  const updateEggBatch = (idx: number, updates: Partial<FrozenEggBatch>) => {
    onChange({
      frozen_egg_batches: form.frozen_egg_batches.map((b, i) =>
        i === idx ? { ...b, ...updates } : b,
      ),
    });
  };

  const removeEggBatch = (idx: number) => {
    onChange({
      frozen_egg_batches: form.frozen_egg_batches.filter((_, i) => i !== idx),
    });
  };

  const addEmbryoBatch = () => {
    if (form.frozen_embryo_batches.length >= 5) return;
    onChange({
      frozen_embryo_batches: [
        ...form.frozen_embryo_batches,
        { age_at_freeze: 0, num_embryos: 0, pgt_tested: false },
      ],
    });
  };

  const updateEmbryoBatch = (idx: number, updates: Partial<FrozenEmbryoBatch>) => {
    onChange({
      frozen_embryo_batches: form.frozen_embryo_batches.map((b, i) =>
        i === idx ? { ...b, ...updates } : b,
      ),
    });
  };

  const removeEmbryoBatch = (idx: number) => {
    onChange({
      frozen_embryo_batches: form.frozen_embryo_batches.filter((_, i) => i !== idx),
    });
  };

  const handleAddEggs = () => {
    setShowEggs(true);
    addEggBatch();
  };

  const handleAddEmbryos = () => {
    setShowEmbryos(true);
    addEmbryoBatch();
  };

  return (
    <div className="space-y-5">
      <p className="text-xs text-stone-500">
        Enter only eggs or embryos you have already frozen. These reserves can be
        included in your forecast. If you have none, leave this section empty.
      </p>

      {!showEggs && !showEmbryos && (
        <div className="flex gap-2">
          <button
            type="button"
            onClick={handleAddEggs}
            className="flex-1 rounded-md border border-stone-300 px-3 py-2 text-sm font-medium text-stone-600 hover:bg-stone-50"
          >
            Add frozen eggs
          </button>
          <button
            type="button"
            onClick={handleAddEmbryos}
            className="flex-1 rounded-md border border-stone-300 px-3 py-2 text-sm font-medium text-stone-600 hover:bg-stone-50"
          >
            Add frozen embryos
          </button>
        </div>
      )}

      {/* Frozen Eggs */}
      {showEggs ? (
        <div>
          <div className="mb-2 flex items-center justify-between">
            <span className="text-sm font-medium text-stone-600">Frozen Eggs</span>
            {form.frozen_egg_batches.length < 5 && (
              <button
                type="button"
                onClick={addEggBatch}
                className="text-xs font-medium text-stone-600 hover:text-stone-800"
              >
                + Add batch
              </button>
            )}
          </div>
          <div className="space-y-2">
            {form.frozen_egg_batches.map((batch, idx) => (
              <FrozenBatchRow
                key={idx}
                type="egg"
                ageAtFreeze={batch.age_at_freeze}
                count={batch.num_eggs}
                onChangeAge={(v) => updateEggBatch(idx, { age_at_freeze: v })}
                onChangeCount={(v) => updateEggBatch(idx, { num_eggs: v })}
                onRemove={() => removeEggBatch(idx)}
              />
            ))}
            {form.frozen_egg_batches.length === 0 && (
              <p className="text-xs text-stone-400">No frozen egg batches.</p>
            )}
          </div>
        </div>
      ) : (
        showEmbryos && (
          <button
            type="button"
            onClick={handleAddEggs}
            className="w-full rounded-md border border-stone-300 px-3 py-2 text-sm font-medium text-stone-600 hover:bg-stone-50"
          >
            Add frozen eggs
          </button>
        )
      )}

      {/* Frozen Embryos */}
      {showEmbryos ? (
        <div>
          <div className="mb-2 flex items-center justify-between">
            <span className="text-sm font-medium text-stone-600">Frozen Embryos</span>
            {form.frozen_embryo_batches.length < 5 && (
              <button
                type="button"
                onClick={addEmbryoBatch}
                className="text-xs font-medium text-stone-600 hover:text-stone-800"
              >
                + Add batch
              </button>
            )}
          </div>
          <div className="space-y-2">
            {form.frozen_embryo_batches.map((batch, idx) => (
              <FrozenBatchRow
                key={idx}
                type="embryo"
                ageAtFreeze={batch.age_at_freeze}
                count={batch.num_embryos}
                pgtTested={batch.pgt_tested}
                onChangePgt={(v) => updateEmbryoBatch(idx, { pgt_tested: v })}
                onChangeAge={(v) => updateEmbryoBatch(idx, { age_at_freeze: v })}
                onChangeCount={(v) => updateEmbryoBatch(idx, { num_embryos: v })}
                onRemove={() => removeEmbryoBatch(idx)}
              />
            ))}
            {form.frozen_embryo_batches.length === 0 && (
              <p className="text-xs text-stone-400">No frozen embryo batches.</p>
            )}
          </div>
        </div>
      ) : (
        showEggs && (
          <button
            type="button"
            onClick={handleAddEmbryos}
            className="w-full rounded-md border border-stone-300 px-3 py-2 text-sm font-medium text-stone-600 hover:bg-stone-50"
          >
            Add frozen embryos
          </button>
        )
      )}
    </div>
  );
}
