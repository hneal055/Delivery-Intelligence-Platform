/**
 * Where a package is in the driver's day:
 *   'pickup'  - has a pickup address and has not been collected yet
 *   'deliver' - in the van (or never had a pickup leg)
 *   'done'    - delivered, or a problem was reported
 */
export function stopPhase(pkg) {
  if (pkg.status === 'delivered' || pkg.status === 'exception') return 'done';
  if (pkg.pickup_address && (pkg.status === 'pending' || pkg.status === 'assigned')) {
    return 'pickup';
  }
  return 'deliver';
}

/** The shipper has said the package can be collected (or there is no pickup). */
export function isReadyForPickup(pkg) {
  return !pkg.pickup_address || Boolean(pkg.ready_at);
}

/** Where the driver should head next for this package. */
export function nextTarget(pkg) {
  if (stopPhase(pkg) === 'pickup') {
    return {
      label: 'PICK UP',
      address: pkg.pickup_address,
      lat: pkg.pickup_lat,
      lon: pkg.pickup_lon,
      instructions: pkg.pickup_instructions,
      unit: null,
    };
  }
  return {
    label: 'DELIVER',
    address: pkg.dest_address,
    lat: pkg.dest_lat,
    lon: pkg.dest_lon,
    instructions: pkg.delivery_instructions,
    unit: pkg.dest_unit,
  };
}
