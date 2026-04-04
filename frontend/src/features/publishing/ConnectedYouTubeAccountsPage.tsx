import { useMemo, useState } from "react";
import { useLocation } from "react-router-dom";

import { PageFrame, SectionCard } from "../../components/ui";
import { getYouTubeConnectUrl } from "../../lib/youtube-api";
import { useDisconnectYouTubeAccount, useSetDefaultYouTubeAccount, useYouTubeAccounts } from "../../hooks/use-youtube-publishing";
import { PublishingEmptyState, PublishingLiveModeNotice, PublishingMetric, formatTimestamp } from "./shared";

function AccountCard({
  accountId,
  channelTitle,
  googleEmail,
  handle,
  isDefault,
  connectedAt,
  tokenExpiryAt,
  onSetDefault,
  onDisconnect,
  busy,
}: {
  accountId: string;
  channelTitle: string;
  googleEmail: string | null;
  handle: string | null;
  isDefault: boolean;
  connectedAt: string;
  tokenExpiryAt: string | null;
  onSetDefault: (accountId: string) => void;
  onDisconnect: (accountId: string) => void;
  busy: boolean;
}) {
  return (
    <article className="rounded-2xl border border-border-card bg-card p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h3 className="font-heading text-lg font-bold text-primary">{channelTitle}</h3>
            {isDefault ? (
              <span className="rounded-full bg-primary-bg px-2.5 py-1 text-[0.68rem] font-bold uppercase tracking-widest text-accent-bright">
                Default
              </span>
            ) : null}
          </div>
          <p className="mt-1 text-sm text-secondary">{googleEmail ?? "Google email unavailable"}</p>
          <p className="mt-1 text-sm text-secondary">{handle ? `Handle: ${handle}` : "No public handle returned"}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            className="rounded-full border border-border-subtle px-3 py-1.5 text-xs font-semibold text-primary transition hover:border-border-active"
            onClick={() => onSetDefault(accountId)}
            type="button"
            disabled={busy || isDefault}
          >
            Set Default
          </button>
          <button
            className="rounded-full border border-error/30 px-3 py-1.5 text-xs font-semibold text-error transition hover:border-error"
            onClick={() => onDisconnect(accountId)}
            type="button"
            disabled={busy}
          >
            Disconnect
          </button>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap gap-3 text-xs text-secondary">
        <span className="rounded-full bg-glass px-3 py-1">Connected: {formatTimestamp(connectedAt)}</span>
        <span className="rounded-full bg-glass px-3 py-1">Token expiry: {formatTimestamp(tokenExpiryAt)}</span>
      </div>
    </article>
  );
}

export function ConnectedYouTubeAccountsPage() {
  const location = useLocation();
  const params = new URLSearchParams(location.search);
  const { data: accounts = [], isLoading, error } = useYouTubeAccounts();
  const disconnectMutation = useDisconnectYouTubeAccount();
  const setDefaultMutation = useSetDefaultYouTubeAccount();
  const [connectError, setConnectError] = useState<string | null>(null);
  const [isConnecting, setIsConnecting] = useState(false);

  const banner = useMemo(() => {
    const youtubeStatus = params.get("youtube");
    if (youtubeStatus === "connected") {
      return "YouTube account connected successfully.";
    }
    if (youtubeStatus === "failed") {
      return (
        params.get("error_message") ??
        `YouTube connection failed: ${params.get("error") ?? "unknown_error"}`
      );
    }
    return null;
  }, [params]);

  async function handleConnect() {
    setConnectError(null);
    setIsConnecting(true);
    try {
      const authorizationUrl = await getYouTubeConnectUrl("/app/publishing/accounts");
      window.location.assign(authorizationUrl);
    } catch (requestError) {
      setConnectError(requestError instanceof Error ? requestError.message : "Unable to start YouTube OAuth.");
    } finally {
      setIsConnecting(false);
    }
  }

  return (
    <PageFrame
      eyebrow="Publishing"
      title="Connected YouTube Accounts"
      description="Connect multiple YouTube channels, choose a default target, and keep upload credentials on the backend."
      actions={
        <button
          className="rounded-full border border-border-active bg-primary-bg px-4 py-2 text-sm font-semibold text-primary"
          onClick={() => void handleConnect()}
          type="button"
          disabled={isConnecting}
        >
          {isConnecting ? "Opening Google..." : "Connect YouTube Account"}
        </button>
      }
      inspector={
        <div className="flex flex-col gap-4">
          <PublishingMetric
            label="Connected"
            value={String(accounts.length)}
            detail="Each platform user can keep multiple channels connected."
          />
          <PublishingMetric
            label="Default"
            value={accounts.find((account) => account.is_default)?.channel_title ?? "None"}
            detail="The default channel is used when a video does not explicitly choose a target account."
          />
        </div>
      }
    >
      <PublishingLiveModeNotice />
      {banner ? (
        <SectionCard title="Connection Status">
          <p className={`text-sm ${params.get("youtube") === "failed" ? "text-error" : "text-secondary"}`}>{banner}</p>
        </SectionCard>
      ) : null}
      {connectError ? (
        <SectionCard title="Connection Error">
          <p className="text-sm text-error">{connectError}</p>
        </SectionCard>
      ) : null}
      {error ? (
        <SectionCard title="Load Error">
          <p className="text-sm text-error">{error instanceof Error ? error.message : "Unable to load accounts."}</p>
        </SectionCard>
      ) : null}
      <SectionCard
        title="Channels"
        subtitle="OAuth uses the FastAPI backend web-server flow, stores encrypted refresh tokens, and fetches the authenticated YouTube channel immediately after callback."
      >
        {isLoading ? (
          <p className="text-sm text-secondary">Loading connected accounts…</p>
        ) : accounts.length === 0 ? (
          <PublishingEmptyState
            title="No YouTube channels connected"
            description="Connect a channel to unlock scheduling, batch slot assignment, and backend-driven YouTube uploads."
          />
        ) : (
          <div className="grid gap-4">
            {accounts.map((account) => (
              <AccountCard
                key={account.id}
                accountId={account.id}
                channelTitle={account.channel_title}
                googleEmail={account.google_account_email}
                handle={account.channel_handle}
                isDefault={account.is_default}
                connectedAt={account.connected_at}
                tokenExpiryAt={account.token_expiry_at}
                onSetDefault={(accountId) => setDefaultMutation.mutate(accountId)}
                onDisconnect={(accountId) => disconnectMutation.mutate(accountId)}
                busy={disconnectMutation.isPending || setDefaultMutation.isPending}
              />
            ))}
          </div>
        )}
      </SectionCard>
    </PageFrame>
  );
}
