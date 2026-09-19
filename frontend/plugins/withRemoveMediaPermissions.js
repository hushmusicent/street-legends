const { withAndroidManifest } = require('@expo/config-plugins');

/**
 * Config plugin to remove READ_MEDIA_IMAGES and READ_MEDIA_VIDEO permissions
 * from the Android manifest for Google Play compliance.
 * 
 * This uses the tools:node="remove" attribute to ensure these permissions
 * are not added by any library through manifest merging.
 */
function withRemoveMediaPermissions(config) {
  return withAndroidManifest(config, async (config) => {
    const androidManifest = config.modResults;
    
    // Ensure the manifest has the tools namespace
    if (!androidManifest.manifest.$) {
      androidManifest.manifest.$ = {};
    }
    androidManifest.manifest.$['xmlns:tools'] = 'http://schemas.android.com/tools';
    
    // Get or create uses-permission array
    if (!androidManifest.manifest['uses-permission']) {
      androidManifest.manifest['uses-permission'] = [];
    }
    
    const permissions = androidManifest.manifest['uses-permission'];
    
    // Remove any existing READ_MEDIA_IMAGES or READ_MEDIA_VIDEO permissions
    const filteredPermissions = permissions.filter(perm => {
      const name = perm.$?.['android:name'] || '';
      return !name.includes('READ_MEDIA_IMAGES') && !name.includes('READ_MEDIA_VIDEO');
    });
    
    // Add explicit removal entries for these permissions
    const permissionsToRemove = [
      'android.permission.READ_MEDIA_IMAGES',
      'android.permission.READ_MEDIA_VIDEO',
    ];
    
    permissionsToRemove.forEach(permName => {
      // Check if removal entry already exists
      const exists = filteredPermissions.some(
        perm => perm.$?.['android:name'] === permName && perm.$?.['tools:node'] === 'remove'
      );
      
      if (!exists) {
        filteredPermissions.push({
          $: {
            'android:name': permName,
            'tools:node': 'remove',
          },
        });
      }
    });
    
    androidManifest.manifest['uses-permission'] = filteredPermissions;
    
    return config;
  });
}

module.exports = withRemoveMediaPermissions;
