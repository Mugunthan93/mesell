# Frontend

This project was generated using [Angular CLI](https://github.com/angular/angular-cli) version 21.2.14.

## Running the app (start here)

This frontend is a **module-federation host (the "shell")** plus one or more
**remotes** (independently-built micro-frontends). You can run the shell on its
own, a remote on its own, or both together.

### One-time setup

```bash
cd frontend
pnpm install
```

### The run commands

| Command | What it starts | Port |
|---|---|---|
| `pnpm start` | The shell, on whatever port Angular picks (can be random) | varies |
| `pnpm start:shell` | The shell, **pinned to a stable port** | http://localhost:4200 |
| `pnpm start:mfe-pricing` | The pricing remote on its own | http://localhost:4201 |

Use `pnpm start:shell` for day-to-day work — it always lands on **4200** so
your bookmark never breaks. (`pnpm start` is kept for compatibility but may pick
a random port.)

### Naming convention (for future remotes)

Every remote gets its own start script following the pattern:

```
start:mfe-<name>
```

So as more micro-frontends are added you'll see `start:mfe-export`,
`start:mfe-onboarding`, and so on — one line per remote, all on their own pinned
ports declared in `angular.json`.

### Run the shell only

```bash
pnpm start:shell
```

Open http://localhost:4200. If a remote is **not** running, the shell still
loads — the page for that remote shows a friendly "couldn't load" fallback
instead of crashing.

### Run a remote only

```bash
pnpm start:mfe-pricing
```

Open http://localhost:4201. This serves the remote standalone, which is handy
when you only care about that one micro-frontend.

### Run the shell + a remote together (two terminals)

The shell loads remotes at runtime, so to see the full app you run both at once,
each in **its own terminal window**:

**Terminal 1 — the shell:**

```bash
pnpm start:shell
```

**Terminal 2 — the pricing remote:**

```bash
pnpm start:mfe-pricing
```

Then open http://localhost:4200. The shell will pull the pricing remote in from
http://localhost:4201 automatically.

### Sanity check: is the remote actually up?

A running remote publishes a small manifest file. Confirm it's live:

```bash
curl http://localhost:4201/remoteEntry.json
```

You should get back a small JSON file (HTTP 200). If you get "connection
refused", the remote terminal isn't running yet.

### Fallback test: kill the remote, the shell should survive

To prove the shell degrades gracefully when a remote is down:

1. Start **only** the shell (`pnpm start:shell`), with no remote running.
2. Open http://localhost:4200 and navigate to the pricing page.
3. You should see a friendly fallback message — **not** a blank screen or a
   crash. The rest of the app keeps working.

If a remote *was* running, stop it (Ctrl-C in its terminal) and refresh the
pricing page in the shell to see the same fallback behaviour.

## Development server

To start a local development server, run:

```bash
ng serve
```

Once the server is running, open your browser and navigate to `http://localhost:4200/`. The application will automatically reload whenever you modify any of the source files.

## Code scaffolding

Angular CLI includes powerful code scaffolding tools. To generate a new component, run:

```bash
ng generate component component-name
```

For a complete list of available schematics (such as `components`, `directives`, or `pipes`), run:

```bash
ng generate --help
```

## Building

To build the project run:

```bash
ng build
```

This will compile your project and store the build artifacts in the `dist/` directory. By default, the production build optimizes your application for performance and speed.

## Running unit tests

To execute unit tests with the [Vitest](https://vitest.dev/) test runner, use the following command:

```bash
ng test
```

## Running end-to-end tests

For end-to-end (e2e) testing, run:

```bash
ng e2e
```

Angular CLI does not come with an end-to-end testing framework by default. You can choose one that suits your needs.

## Additional Resources

For more information on using the Angular CLI, including detailed command references, visit the [Angular CLI Overview and Command Reference](https://angular.dev/tools/cli) page.
