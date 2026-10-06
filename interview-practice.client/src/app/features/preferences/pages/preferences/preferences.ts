import { Component, viewChild } from '@angular/core';
import { NgIcon, provideIcons } from '@ng-icons/core';
import { lucideFileText, lucideSlidersHorizontal } from '@ng-icons/lucide';
import { HlmTabsImports } from '@spartan-ng/helm/tabs';
import { ConfirmsLeaving } from '@app/core/guards/leave-confirmation-guard';
import { DocumentLibrary } from './components/document-library/document-library';
import { ModelDefaults } from './components/model-defaults/model-defaults';

/**
 * Everything kept apart from the candidate-facing flow: the model defaults of each phase, and the
 * library of saved Documents. Both tabs stay mounted while hidden, so unsaved edits survive a
 * switch between them.
 */
@Component({
  selector: 'app-preferences',
  providers: [provideIcons({ lucideFileText, lucideSlidersHorizontal })],
  imports: [DocumentLibrary, HlmTabsImports, ModelDefaults, NgIcon],
  templateUrl: './preferences.html',
})
export class Preferences implements ConfirmsLeaving {
  private readonly modelDefaults = viewChild.required(ModelDefaults);

  leaveConfirmation(): string | null {
    return this.modelDefaults().dirty()
      ? 'You have unsaved changes to your model defaults. Leave without saving them?'
      : null;
  }
}
