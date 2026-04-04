import { useEffect, useMemo, useState } from "react";

import { PageFrame, SectionCard } from "../../components/ui";
import { useCreatePublishSchedule, usePublishSchedules, useUpdatePublishSchedule, useYouTubeAccounts } from "../../hooks/use-youtube-publishing";
import type { PublishSchedulePayload } from "../../types/youtube";
import { PublishingEmptyState, PublishingLiveModeNotice, PublishingMetric, formatTimestamp } from "./shared";

function availableTimezones(): string[] {
  if (typeof Intl !== "undefined" && "supportedValuesOf" in Intl) {
    try {
      return (Intl as typeof Intl & { supportedValuesOf: (key: string) => string[] }).supportedValuesOf("timeZone");
    } catch {
      return [];
    }
  }
  return [];
}

export function ScheduleSettingsPage() {
  const { data: accounts = [], isLoading: accountsLoading } = useYouTubeAccounts();
  const { data: schedules = [], isLoading: schedulesLoading, error } = usePublishSchedules();
  const createMutation = useCreatePublishSchedule();
  const updateMutation = useUpdatePublishSchedule();
  const [selectedAccountId, setSelectedAccountId] = useState("");
  const [timezoneName, setTimezoneName] = useState(Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC");
  const [slots, setSlots] = useState(["09:00"]);
  const timezones = useMemo(() => availableTimezones(), []);

  useEffect(() => {
    if (!selectedAccountId && accounts[0]?.id) {
      setSelectedAccountId(accounts[0].id);
    }
  }, [accounts, selectedAccountId]);

  const selectedSchedule = schedules.find((schedule) => schedule.youtube_account_id === selectedAccountId) ?? null;

  useEffect(() => {
    if (!selectedSchedule) {
      return;
    }
    setTimezoneName(selectedSchedule.timezone_name);
    setSlots(selectedSchedule.slots_local.length ? selectedSchedule.slots_local : ["09:00"]);
  }, [selectedSchedule]);

  async function handleSave() {
    const payload: PublishSchedulePayload = {
      youtube_account_id: selectedAccountId,
      timezone_name: timezoneName,
      slots_local: slots.filter(Boolean),
      is_active: true,
    };
    if (selectedSchedule) {
      await updateMutation.mutateAsync({ scheduleId: selectedSchedule.id, payload });
      return;
    }
    await createMutation.mutateAsync(payload);
  }

  return (
    <PageFrame
      eyebrow="Publishing"
      title="Schedule Settings"
      description="Configure daily local-time publish slots per YouTube account. The backend converts those slots to UTC and auto-assigns the next free future slot during scheduling."
      inspector={
        <div className="grid gap-4">
          <PublishingMetric label="Accounts" value={String(accounts.length)} detail="Each channel keeps its own timezone and slot list." />
          <PublishingMetric label="Schedules" value={String(schedules.length)} detail="One active daily schedule per connected YouTube account." />
        </div>
      }
    >
      <PublishingLiveModeNotice />
      {error ? (
        <SectionCard title="Load Error">
          <p className="text-sm text-error">{error instanceof Error ? error.message : "Unable to load schedules."}</p>
        </SectionCard>
      ) : null}
      <SectionCard
        title="Per-Account Daily Publishing Schedule"
        subtitle="If you want one video per day, add one slot. If you want two or more, add more slots. Each slot is a local wall-clock time stored against the selected account."
      >
        {accountsLoading || schedulesLoading ? (
          <p className="text-sm text-secondary">Loading account schedules…</p>
        ) : accounts.length === 0 ? (
          <PublishingEmptyState
            title="Connect a YouTube account first"
            description="You need at least one connected channel before you can define a daily publishing schedule."
          />
        ) : (
          <div className="grid gap-5">
            <label className="flex flex-col gap-2">
              <span className="text-[0.68rem] font-bold uppercase tracking-widest text-muted">YouTube Account</span>
              <select
                className="rounded-xl border border-border-subtle bg-glass px-4 py-3 text-sm text-primary"
                value={selectedAccountId}
                onChange={(event) => setSelectedAccountId(event.target.value)}
              >
                {accounts.map((account) => (
                  <option key={account.id} value={account.id}>
                    {account.channel_title}
                  </option>
                ))}
              </select>
            </label>

            <label className="flex flex-col gap-2">
              <span className="text-[0.68rem] font-bold uppercase tracking-widest text-muted">Timezone</span>
              {timezones.length > 0 ? (
                <select
                  className="rounded-xl border border-border-subtle bg-glass px-4 py-3 text-sm text-primary"
                  value={timezoneName}
                  onChange={(event) => setTimezoneName(event.target.value)}
                >
                  {timezones.map((timezone) => (
                    <option key={timezone} value={timezone}>
                      {timezone}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  className="rounded-xl border border-border-subtle bg-glass px-4 py-3 text-sm text-primary"
                  value={timezoneName}
                  onChange={(event) => setTimezoneName(event.target.value)}
                />
              )}
            </label>

            <div className="grid gap-3">
              <div className="flex items-center justify-between">
                <span className="text-[0.68rem] font-bold uppercase tracking-widest text-muted">Daily Slots</span>
                <button
                  className="rounded-full border border-border-subtle px-3 py-1.5 text-xs font-semibold text-primary"
                  onClick={() => setSlots((current) => [...current, "12:00"])}
                  type="button"
                >
                  Add Slot
                </button>
              </div>
              {slots.map((slot, index) => (
                <div key={`${slot}-${index}`} className="flex items-center gap-3">
                  <input
                    className="w-40 rounded-xl border border-border-subtle bg-glass px-4 py-3 text-sm text-primary"
                    value={slot}
                    onChange={(event) =>
                      setSlots((current) => current.map((item, itemIndex) => (itemIndex === index ? event.target.value : item)))
                    }
                    placeholder="09:00"
                  />
                  <button
                    className="rounded-full border border-border-subtle px-3 py-1.5 text-xs font-semibold text-primary"
                    onClick={() => setSlots((current) => current.filter((_, itemIndex) => itemIndex !== index))}
                    type="button"
                    disabled={slots.length === 1}
                  >
                    Remove
                  </button>
                </div>
              ))}
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <button
                className="rounded-full border border-border-active bg-primary-bg px-4 py-2 text-sm font-semibold text-primary"
                onClick={() => void handleSave()}
                type="button"
                disabled={createMutation.isPending || updateMutation.isPending || !selectedAccountId}
              >
                {selectedSchedule ? "Update Schedule" : "Create Schedule"}
              </button>
              {createMutation.error || updateMutation.error ? (
                <p className="text-sm text-error">
                  {(createMutation.error ?? updateMutation.error) instanceof Error
                    ? ((createMutation.error ?? updateMutation.error) as Error).message
                    : "Unable to save schedule."}
                </p>
              ) : null}
            </div>
          </div>
        )}
      </SectionCard>

      {selectedSchedule ? (
        <SectionCard title="Next Free Slots" subtitle="The backend already converts your local account schedule into future UTC publish candidates.">
          <div className="grid gap-3">
            {selectedSchedule.next_available_slots_utc.map((slot) => (
              <div key={slot} className="rounded-xl border border-border-subtle bg-glass px-4 py-3 text-sm text-secondary">
                {formatTimestamp(slot)}
              </div>
            ))}
            <p className="text-xs text-muted">Last updated {formatTimestamp(selectedSchedule.updated_at)}</p>
          </div>
        </SectionCard>
      ) : null}
    </PageFrame>
  );
}
