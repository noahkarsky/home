from django.urls import path

from . import views


urlpatterns = [

    path( '',
          views.Floorplan3dView.as_view(),
          name = 'floorplan3d_home' ),

    path( 'designer',
          views.Floorplan3dDesignerView.as_view(),
          name = 'floorplan3d_designer' ),

    path( 'apply',
          views.Floorplan3dApplyView.as_view(),
          name = 'floorplan3d_apply' ),
]
