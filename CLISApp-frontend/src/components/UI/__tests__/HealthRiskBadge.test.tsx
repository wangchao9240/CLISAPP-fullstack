import React from 'react';
import { StyleSheet } from 'react-native';
import { create } from 'react-test-renderer';

jest.mock('react-native-vector-icons/MaterialCommunityIcons', () => {
  const { Text } = require('react-native');
  return ({ name, ...props }: any) => <Text {...props}>{name}</Text>;
});

const {
  HealthRiskBadge,
  RISK_LEVEL_VISUALS,
} = require('../HealthRiskBadge') as typeof import('../HealthRiskBadge');

const getBadge = (riskLevel?: string) =>
  create(<HealthRiskBadge riskLevel={riskLevel} testID="health-risk-badge" />);

const getBadgeNode = (renderer: ReturnType<typeof create>) =>
  renderer.root.find(
    (node) => node.props.testID === 'health-risk-badge' && Array.isArray(node.props.style),
  );

const getBadgeStyle = (renderer: ReturnType<typeof create>) =>
  StyleSheet.flatten(getBadgeNode(renderer).props.style);

describe('HealthRiskBadge', () => {
  it('renders the Good badge styling and label', () => {
    const renderer = getBadge('Good');

    expect(renderer.root.findByProps({ children: 'Good' })).toBeDefined();
    expect(getBadgeStyle(renderer)?.backgroundColor).toBe(RISK_LEVEL_VISUALS.Good.bg);
  });

  it('renders the Moderate badge styling and label', () => {
    const renderer = getBadge('Moderate');

    expect(renderer.root.findByProps({ children: 'Moderate' })).toBeDefined();
    expect(getBadgeStyle(renderer)?.backgroundColor).toBe(RISK_LEVEL_VISUALS.Moderate.bg);
  });

  it('renders the Unhealthy badge styling and label', () => {
    const renderer = getBadge('Unhealthy');

    expect(renderer.root.findByProps({ children: 'Unhealthy' })).toBeDefined();
    expect(getBadgeStyle(renderer)?.backgroundColor).toBe(RISK_LEVEL_VISUALS.Unhealthy.bg);
  });

  it('renders the Hazardous badge styling and label', () => {
    const renderer = getBadge('Hazardous');

    expect(renderer.root.findByProps({ children: 'Hazardous' })).toBeDefined();
    expect(getBadgeStyle(renderer)?.backgroundColor).toBe(RISK_LEVEL_VISUALS.Hazardous.bg);
  });

  it('renders the Unknown fallback when riskLevel is undefined', () => {
    const renderer = getBadge(undefined);

    expect(renderer.root.findByProps({ children: 'Unknown' })).toBeDefined();
    expect(getBadgeStyle(renderer)?.backgroundColor).toBe(RISK_LEVEL_VISUALS.Unknown.bg);
  });

  it('renders the Unknown fallback when riskLevel is unrecognized', () => {
    const renderer = getBadge('Foobar');

    expect(renderer.root.findByProps({ children: 'Unknown' })).toBeDefined();
    expect(getBadgeStyle(renderer)?.backgroundColor).toBe(RISK_LEVEL_VISUALS.Unknown.bg);
  });

  it('uses a default accessibilityLabel that includes the level name', () => {
    const renderer = getBadge('Unhealthy');

    expect(getBadgeNode(renderer).props.accessibilityLabel).toBe('Unhealthy air/health risk');
  });
});
