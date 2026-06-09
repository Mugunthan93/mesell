# Terminal

**Import:** `import { Terminal, TerminalService } from 'primeng/terminal'`
**Selector:** `p-terminal`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| welcomeMessage | `string \| undefined` | undefined | Initial welcome text displayed in the terminal |
| prompt | `string \| undefined` | undefined | Prompt prefix string (e.g., `'$'`) |
| styleClass | `string \| undefined` | undefined | CSS class |

## TerminalService API

```typescript
import { TerminalService } from 'primeng/terminal';

// In component
constructor(private terminalService: TerminalService) {
  this.terminalService.commandHandler.subscribe(command => {
    // process command
    this.terminalService.sendCommand(`Output of: ${command}`);
  });
}
```

## Usage Example

```html
<!-- Basic terminal -->
<p-terminal welcomeMessage="MeeSell CLI v1.0" prompt="meesell$" />
```

```typescript
// In component (inject TerminalService)
readonly terminalSvc = inject(TerminalService);

ngOnInit() {
  this.terminalSvc.commandHandler.subscribe(cmd => {
    const response = this.processCommand(cmd);
    this.terminalSvc.sendCommand(response);
  });
}
```

## Notes

- `TerminalService` must be provided at the component level or module level.
- User input is piped through `TerminalService.commandHandler` Observable.
- Call `terminalService.sendCommand(responseText)` to write a response line.
- Niche component — primarily useful for admin/debug interfaces, not customer-facing UI.
