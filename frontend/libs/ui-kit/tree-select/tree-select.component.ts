import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';
import { TreeSelect } from 'primeng/treeselect';
import type { TreeNode } from 'primeng/api';

export interface MeeTreeNode {
  label: string;
  value: unknown;
  children?: MeeTreeNode[];
}

function toTreeNode(node: MeeTreeNode): TreeNode {
  return {
    label: node.label,
    data: node.value,
    children: node.children?.map(toTreeNode),
  };
}

@Component({
  selector: 'mee-tree-select',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [TreeSelect],
  template: `
    <p-treeselect
      [options]="treeNodes()"
      [placeholder]="placeholder()"
      [loading]="loading()"
      selectionMode="single"
      class="w-full"
      [style]="{ minHeight: '44px', width: '100%' }"
      (onNodeSelect)="onNodeSelect($event)"
    />
  `,
})
export class MeeTreeSelectComponent {
  readonly nodes = input.required<MeeTreeNode[]>();
  readonly placeholder = input<string>('Select category');
  readonly loading = input<boolean>(false);

  readonly value_change = output<MeeTreeNode>();

  get treeNodes(): () => TreeNode[] {
    return () => this.nodes().map(toTreeNode);
  }

  onNodeSelect(event: { node: TreeNode }): void {
    if (event.node) {
      const selected: MeeTreeNode = {
        label: event.node.label ?? '',
        value: event.node.data,
        children: undefined,
      };
      this.value_change.emit(selected);
    }
  }
}
