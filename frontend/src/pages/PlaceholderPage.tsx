import { Empty, Typography } from 'antd'

export default function PlaceholderPage({ name }: { name: string }) {
  return (
    <Empty
      style={{ marginTop: 120 }}
      description={
        <Typography.Text type="secondary">
          「{name}」模块尚未开发，按开发计划将在后续阶段实现。
        </Typography.Text>
      }
    />
  )
}
