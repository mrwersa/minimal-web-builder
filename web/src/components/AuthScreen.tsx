import { FormEvent, useState } from "react";
import { Sparkles } from "lucide-react";
import { useAuthStore } from "../authStore";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { InlineError } from "./ui/field";
import { Spinner } from "./ui/spinner";

export default function AuthScreen() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const login = useAuthStore((state) => state.login);
  const register = useAuthStore((state) => state.register);
  const submitting = useAuthStore((state) => state.submitting);
  const error = useAuthStore((state) => state.error);

  async function submitCredentials() {
    if (submitting) return;
    await (mode === "login" ? login(email, password) : register(email, password));
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    void submitCredentials();
  }

  function changeMode() {
    setMode(mode === "login" ? "register" : "login");
    useAuthStore.setState({ error: null });
  }

  return (
    <main className="flex h-full items-center justify-center bg-background px-4 text-foreground">
      <section className="w-full max-w-sm rounded-2xl border border-border bg-surface p-7 shadow-sm">
        <div className="mb-6 flex items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <Sparkles className="h-5 w-5" />
          </span>
          <div>
            <h1 className="font-semibold">Minimal Web Builder</h1>
            <p className="text-sm text-muted-foreground">
              {mode === "login" ? "Welcome back" : "Create your workspace"}
            </p>
          </div>
        </div>

        <form className="space-y-4" onSubmit={submit}>
          <label className="block space-y-1.5 text-sm font-medium">
            Email
            <Input
              autoComplete="email"
              autoFocus
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </label>
          <label className="block space-y-1.5 text-sm font-medium">
            Password
            <Input
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              minLength={12}
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
            {mode === "register" && (
              <span className="block text-xs font-normal text-muted-foreground">
                Use at least 12 characters.
              </span>
            )}
          </label>
          {error && <InlineError message={error} onRetry={() => void submitCredentials()} />}
          <Button className="w-full" disabled={submitting} type="submit">
            {submitting && <Spinner size="sm" />}
            {mode === "login" ? "Sign in" : "Create account"}
          </Button>
        </form>

        <button
          className="mt-5 w-full text-sm text-muted-foreground hover:text-primary"
          onClick={changeMode}
          type="button"
        >
          {mode === "login"
            ? "New here? Create an account"
            : "Already have an account? Sign in"}
        </button>
      </section>
    </main>
  );
}
