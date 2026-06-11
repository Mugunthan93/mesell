import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MeeTreeSelectComponent, MeeTreeNode } from './tree-select.component';

const MOCK_NODES: MeeTreeNode[] = [
  {
    label: 'Electronics',
    value: 'electronics',
    children: [
      { label: 'Phones', value: 'phones' },
      { label: 'Laptops', value: 'laptops' },
    ],
  },
];

describe('MeeTreeSelectComponent', () => {
  let fixture: ComponentFixture<MeeTreeSelectComponent>;
  let comp: MeeTreeSelectComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MeeTreeSelectComponent, NoopAnimationsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(MeeTreeSelectComponent);
    comp = fixture.componentInstance;
    fixture.componentRef.setInput('nodes', MOCK_NODES);
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(comp).toBeTruthy();
  });

  it('should default placeholder to Select category', () => {
    expect(comp.placeholder()).toBe('Select category');
  });

  it('should convert MeeTreeNode[] to TreeNode[]', () => {
    const items = comp.treeNodes();
    expect(items.length).toBe(1);
    expect(items[0].label).toBe('Electronics');
    expect(items[0].children?.length).toBe(2);
  });

  it('should emit value_change on node select', () => {
    const emitted: MeeTreeNode[] = [];
    comp.value_change.subscribe((n: MeeTreeNode) => { emitted.push(n); });
    comp.onNodeSelect({ node: { label: 'Phones', data: 'phones' } });
    expect(emitted.length).toBe(1);
    expect(emitted[0].label).toBe('Phones');
    expect(emitted[0].value).toBe('phones');
  });
});
