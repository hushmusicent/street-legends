const { withGradleProperties, withProjectBuildGradle } = require('@expo/config-plugins');

const MARKER = '// BUILDCONFIG-FIX-V4';

/**
 * Fix the EAS build failure for AGP 9.x, v4.
 *
 * expo-log-box defines custom BuildConfig fields, but AGP 9 disables
 * BuildConfig generation by default. The v1 fix (a gradle.properties
 * flag) was removed in AGP 9. v2/v3 set buildConfig from the root
 * build.gradle inside a subprojects afterEvaluate block — the block
 * landed in the generated file (confirmed at line 27), but AGP 9
 * rejects late mutation via afterEvaluate, so the build still died
 * during configuration before any task ran.
 * v4 configures buildFeatures when each Android plugin is applied
 * (plugins.withId + extensions.configure), which runs during the
 * module's own evaluation — before AGP finalizes the DSL. This is the
 * mechanism AGP 9's own migration guide prescribes, applied to every
 * Android library and app module.
 */
function withBuildConfig(config) {
  // 1. Make sure the removed AGP 9 property is NOT set.
  config = withGradleProperties(config, (config) => {
    const key = 'android.defaults.buildfeatures.buildconfig';
    config.modResults = config.modResults.filter((p) => p.key !== key);
    return config;
  });
  // 2. Enable buildConfig for all Android modules at plugin-apply time.
  config = withProjectBuildGradle(config, (config) => {
    const block = `
${MARKER}
subprojects {
    plugins.withId('com.android.library') {
        extensions.configure(com.android.build.gradle.LibraryExtension) {
            buildFeatures {
                buildConfig = true
            }
        }
    }
    plugins.withId('com.android.application') {
        extensions.configure(com.android.build.gradle.AppExtension) {
            buildFeatures {
                buildConfig = true
            }
        }
    }
}
`;
    if (!config.modResults.contents.includes(MARKER)) {
      config.modResults.contents += block;
    }
    return config;
  });
  return config;
}

module.exports = withBuildConfig;
